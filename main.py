import os
import argparse

def remove_spikes(
    input_file_path,
    output_file_path,
    minimum_angle,
    is_verbose):
    print("Not implemented yet!")
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