"""
This script processes polygons in a GeoPackage file, removing spikes by filtering out
vertices that form angles sharper than a specified threshold.
"""

import argparse
import os
import warnings
from typing import Tuple, Union

import fiona
import numpy as np
from fiona.errors import FionaDeprecationWarning
from pyproj import CRS
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.validation import make_valid

# Suppress the Fiona class deprecation warning
warnings.filterwarnings('ignore', category=FionaDeprecationWarning)
# Suppress the PyProj warning about lossy conversion
warnings.filterwarnings('ignore', category=UserWarning)


def calculate_angle(p0: Tuple[float, float], p1: Tuple[float, float],
                    p2: Tuple[float, float]) -> float:
    """
    Calculate the angle between three points in 2D space.

    Args:
        p0 (Tuple[float, float]): Coordinates of the first point.
        p1 (Tuple[float, float]): Coordinates of the second point (vertex).
        p2 (Tuple[float, float]): Coordinates of the third point.

    Returns:
        float: Angle in degrees.
    """
    # Calculate vectors from p1 to p0 and p1 to p2
    v1 = np.array(p0) - np.array(p1)
    v2 = np.array(p2) - np.array(p1)

    # Calculate dot product and norms
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)

    # Handle cases where vectors are extremely small to avoid division by zero
    if norm_v1 < 1e-10 or norm_v2 < 1e-10:
        return 180.0

    # Calculate and return the angle using the dot product formula
    cosine_angle = np.clip(dot_product / (norm_v1 * norm_v2), -1.0, 1.0)
    return np.degrees(np.arccos(cosine_angle))


def filter_polygon(poly: Polygon, feature_id: str, min_angle: float,
                   verbose: bool) -> Tuple[Polygon, int]:
    """
    Filter a polygon by removing vertices that form angles less than the specified minimum.

    Args:
        poly (Polygon): Input polygon to filter.
        feature_id (str): Identifier for the feature being processed.
        min_angle (float): Minimum angle threshold in degrees.
        verbose (bool): Flag to enable verbose output.

    Returns:
        Tuple[Polygon, int]: Filtered polygon and number of spikes removed.
    """
    def check_angle(prev, curr, next):
        angle = calculate_angle(prev, curr, next)
        if angle >= min_angle:
            return curr, 0
        return None, 1

    coords = list(poly.exterior.coords)
    new_coords = []
    spikes_removed = 0

    # Iterate through all vertices except the last (which is the same as the first)
    for i in range(len(coords) - 1):
        prev, curr, next = coords[i - 1], coords[i], coords[(i + 1) % (len(coords) - 1)]
        point, spike_removed = check_angle(prev, curr, next)
        if point is not None:
            new_coords.append(point)
        spikes_removed += spike_removed

    # Handle the case where we need to adjust the start/end point
    if len(new_coords) >= 3:
        start_end_point, spike_removed = check_angle(new_coords[-1], new_coords[0], new_coords[1])
        if start_end_point is None:
            # If the start/end point forms a spike, replace it with the midpoint
            midpoint = tuple((np.array(new_coords[-1]) + np.array(new_coords[1])) / 2)
            new_coords[0] = midpoint
            spikes_removed += spike_removed
    else:
        # If we don't have enough points to form a valid polygon, return an empty one
        return Polygon(), spikes_removed

    # Close the polygon by adding the first point at the end
    new_coords.append(new_coords[0])
    filtered_poly = Polygon(new_coords)

    # Ensure the resulting polygon is valid
    if not filtered_poly.is_valid:
        filtered_poly = make_valid(filtered_poly)

    return filtered_poly, spikes_removed


def filter_vertices(geometry: Union[Polygon, MultiPolygon], feature_id: str,
                    min_angle: float, verbose: bool) -> Tuple[Union[Polygon, MultiPolygon], int]:
    """
    Filter vertices of a geometry (Polygon or MultiPolygon) based on the minimum angle.

    Args:
        geometry (Union[Polygon, MultiPolygon]): Input geometry to filter.
        feature_id (str): Identifier for the feature being processed.
        min_angle (float): Minimum angle threshold in degrees.
        verbose (bool): Flag to enable verbose output.

    Returns:
        Tuple[Union[Polygon, MultiPolygon], int]: Filtered geometry and total spikes removed.

    Raises:
        ValueError: If the input geometry is not a Polygon or MultiPolygon.
    """
    if isinstance(geometry, Polygon):
        return filter_polygon(geometry, feature_id, min_angle, verbose)
    elif isinstance(geometry, MultiPolygon):
        filtered_polys = []
        total_spikes_removed = 0
        for i, poly in enumerate(geometry.geoms):
            filtered_poly, spikes_removed = filter_polygon(poly, f"{feature_id}_{i + 1}", min_angle, verbose)
            if not filtered_poly.is_empty:
                filtered_polys.extend([filtered_poly] if isinstance(filtered_poly, Polygon) else filtered_poly.geoms)
            total_spikes_removed += spikes_removed

        # Determine the appropriate return type based on the number of filtered polygons
        if len(filtered_polys) > 1:
            return MultiPolygon(filtered_polys), total_spikes_removed
        elif len(filtered_polys) == 1:
            return filtered_polys[0], total_spikes_removed
        else:
            return Polygon(), total_spikes_removed
    else:
        raise ValueError(f"Unsupported geometry type: {type(geometry)}")


def unspike_gpkg(input_path: str, output_path: str, min_angle: float,
                 verbose: bool) -> int:
    """
    Process a GeoPackage file to remove spikes from polygons.

    Args:
        input_path (str): Path to the input GeoPackage file.
        output_path (str): Path to the output GeoPackage file.
        min_angle (float): Minimum angle threshold in degrees.
        verbose (bool): Flag to enable verbose output.

    Returns:
        int: Total number of spikes removed.
    """
    total_spikes_removed = 0
    features_processed = features_skipped = 0

    with fiona.open(input_path, 'r') as src:
        meta = src.meta
        input_crs = CRS(src.crs)

        if verbose:
            print(f"Input CRS: {input_crs}")

        # Define a new schema that supports both Polygon and MultiPolygon
        new_schema = {'geometry': 'MultiPolygon', 'properties': meta['schema']['properties']}

        if verbose:
            print(f"Processing {len(src)} features...")

        with fiona.open(output_path, 'w', crs=src.crs, driver='GPKG', schema=new_schema) as dst:
            for feature in src:
                # Convert the feature's geometry to a shapely object
                geom = shape(feature['geometry'])
                filtered_geom, spikes_removed = filter_vertices(geom, feature['id'], min_angle, verbose)
                total_spikes_removed += spikes_removed

                if filtered_geom.is_valid and not filtered_geom.is_empty:
                    # Ensure the output geometry is always a MultiPolygon
                    if isinstance(filtered_geom, Polygon):
                        filtered_geom = MultiPolygon([filtered_geom])
                    feature['geometry'] = mapping(filtered_geom)
                    dst.write({'geometry': feature['geometry'], 'properties': feature['properties']})
                    features_processed += 1
                else:
                    features_skipped += 1

                # Print progress update every 100 features if verbose mode is on
                if verbose and (features_processed + features_skipped) % 100 == 0:
                    print(f"Processed {features_processed + features_skipped} features...")

    if verbose:
        print(f"\nProcessing complete:")
        print(f"Features processed: {features_processed}")
        print(f"Features skipped: {features_skipped}")
        print(f"Total spikes removed: {total_spikes_removed}")

    return total_spikes_removed


def main():
    """
    Main function to parse arguments and run the unspike_gpkg function.
    """
    parser = argparse.ArgumentParser(
        description="Remove spikes from polygons by filtering out vertices forming angles sharper than a threshold angle in 3D space")
    parser.add_argument('-i', '--input', required=True, help='Path to the input geopackage file.')
    parser.add_argument('-o', '--output', help='Path to the output geopackage file.')
    parser.add_argument('-a', '--angle', required=True, type=float, help='Minimum angle threshold (degrees).')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output.')

    args = parser.parse_args()

    # Generate output file name if not provided
    output_path = args.output or f"{os.path.splitext(args.input)[0]}_unspiked{os.path.splitext(args.input)[1]}"

    if args.verbose:
        print(f"Input file: {args.input}")
        print(f"Output file: {output_path}")
        print(f"Minimum angle (degrees): {args.angle}")

    total_spikes_removed = unspike_gpkg(args.input, output_path, args.angle, args.verbose)

    # Print final summary
    print(
        f"\nProcess completed. {total_spikes_removed} spike/s removed." if total_spikes_removed > 0 else "\nProcess completed. No spikes found.")


if __name__ == "__main__":
    main()