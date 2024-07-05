import os
import argparse
import fiona
import warnings
from fiona.errors import FionaDeprecationWarning
from shapely.geometry import shape, mapping, Polygon, MultiPolygon

# suppress the fiona class deprecation warning
warnings.filterwarnings('ignore', category=FionaDeprecationWarning)

def remove_spikes(
    input_file_path,
    output_file_path,
    minimum_angle,
    is_verbose):
        with fiona.open(input_file_path, 'r') as src:
            #grab the metadata
            metadata = src.meta

            #define a new schema for the output file
            new_schema = {
                'geometry' : 'MultiPolygon',
                'properties' : metadata['schema']['properties']
            }

            #open the output file in write mode
            with fiona.open(output_file_path, 'w', crs=src.crs, driver='GPKG', schema=new_schema) as dst:
                #iterate the geometries of the input file
                for feature in src:
                    geom = shape(feature['geometry'])
                    print(geom)
            print(metadata)
        return 0

def main():
    parser = argparse.ArgumentParser(description="Remove spikes from polygons by filtering out vertices forming angles sharper than a threshold angle")
    parser.add_argument('-i', '--input', required=True, help='Path to the input geopackage file.')
    parser.add_argument('-o', '--output', help='Path to the output geopackage file.')
    parser.add_argument('-a', '--angle', required=True, type=float, help='Minimum angle threshold (degrees).')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose.')

    args = parser.parse_args()

    input_path = args.input
    min_angle = args.angle
    verbose = args.verbose

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        #none supplied, use default
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_unspiked{ext}"

    # Find and remove spikes
    total_spikes_removed = remove_spikes(
        input_path,
        output_path,
        min_angle,
        verbose)

    # Print the summary message
    if total_spikes_removed > 0:
        print(f"{total_spikes_removed} spikes removed.")
    else:
        print("No spikes found.")


if __name__ == "__main__":
    main()