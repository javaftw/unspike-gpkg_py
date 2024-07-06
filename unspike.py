import argparse
import fiona
import numpy as np
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.validation import make_valid
import os
import warnings
from fiona.errors import FionaDeprecationWarning
from pyproj import CRS

# suppress the fiona class deprecation warning
warnings.filterwarnings('ignore', category=FionaDeprecationWarning)
# suppress the pyproj warning about lossy conversion
warnings.filterwarnings('ignore', category=UserWarning)


def calculate_angle(p0, p1, p2):
    v1 = np.array(p0) - np.array(p1)
    v2 = np.array(p2) - np.array(p1)

    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)

    if norm_v1 < 1e-10 or norm_v2 < 1e-10:
        return 180.0

    cosine_angle = np.clip(dot_product / (norm_v1 * norm_v2), -1.0, 1.0)
    return np.degrees(np.arccos(cosine_angle))


def filter_polygon(poly, feature_id, min_angle, verbose):
    def check_angle(prev, curr, next):
        angle = calculate_angle(prev, curr, next)
        if angle >= min_angle:
            return curr, 0
        return None, 1

    coords = list(poly.exterior.coords)
    new_coords = []
    spikes_removed = 0

    for i in range(len(coords) - 1):
        prev, curr, next = coords[i - 1], coords[i], coords[(i + 1) % (len(coords) - 1)]
        point, spike_removed = check_angle(prev, curr, next)
        if point is not None:
            new_coords.append(point)
        spikes_removed += spike_removed

    if len(new_coords) >= 3:
        start_end_point, spike_removed = check_angle(new_coords[-1], new_coords[0], new_coords[1])
        if start_end_point is None:
            midpoint = tuple((np.array(new_coords[-1]) + np.array(new_coords[1])) / 2)
            new_coords[0] = midpoint
            spikes_removed += spike_removed
    else:
        return Polygon(), spikes_removed

    new_coords.append(new_coords[0])
    filtered_poly = Polygon(new_coords)

    if not filtered_poly.is_valid:
        filtered_poly = make_valid(filtered_poly)

    return filtered_poly, spikes_removed


def filter_vertices(geometry, feature_id, min_angle, verbose):
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

        if len(filtered_polys) > 1:
            return MultiPolygon(filtered_polys), total_spikes_removed
        elif len(filtered_polys) == 1:
            return filtered_polys[0], total_spikes_removed
        else:
            return Polygon(), total_spikes_removed
    else:
        raise ValueError(f"Unsupported geometry type: {type(geometry)}")


def unspike_gpkg(input_path, output_path, min_angle, verbose):
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
                geom = shape(feature['geometry'])
                filtered_geom, spikes_removed = filter_vertices(geom, feature['id'], min_angle, verbose)
                total_spikes_removed += spikes_removed

                if filtered_geom.is_valid and not filtered_geom.is_empty:
                    if isinstance(filtered_geom, Polygon):
                        filtered_geom = MultiPolygon([filtered_geom])
                    feature['geometry'] = mapping(filtered_geom)
                    dst.write({'geometry': feature['geometry'], 'properties': feature['properties']})
                    features_processed += 1
                else:
                    features_skipped += 1

                if verbose and (features_processed + features_skipped) % 100 == 0:
                    print(f"Processed {features_processed + features_skipped} features...")

    if verbose:
        print(f"\nProcessing complete:")
        print(f"Features processed: {features_processed}")
        print(f"Features skipped: {features_skipped}")
        print(f"Total spikes removed: {total_spikes_removed}")

    return total_spikes_removed


def main():
    parser = argparse.ArgumentParser(
        description="Remove spikes from polygons by filtering out vertices forming angles sharper than a threshold angle in 3D space")
    parser.add_argument('-i', '--input', required=True, help='Path to the input geopackage file.')
    parser.add_argument('-o', '--output', help='Path to the output geopackage file.')
    parser.add_argument('-a', '--angle', required=True, type=float, help='Minimum angle threshold (degrees).')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output.')

    args = parser.parse_args()

    output_path = args.output or f"{os.path.splitext(args.input)[0]}_unspiked{os.path.splitext(args.input)[1]}"

    if args.verbose:
        print(f"Input file: {args.input}")
        print(f"Output file: {output_path}")
        print(f"Minimum angle (degrees): {args.angle}")

    total_spikes_removed = unspike_gpkg(args.input, output_path, args.angle, args.verbose)

    print(
        f"\nProcess completed. {total_spikes_removed} spike/s removed." if total_spikes_removed > 0 else "\nProcess completed. No spikes found.")


if __name__ == "__main__":
    main()