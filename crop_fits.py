"""
Crop fits files

"""

import os
import glob
import sys
from astropy.io import fits


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Decompress fits files.')
    parser.add_argument('files', nargs='+',  # <-- This is the key change
                        help='Glob pattern or list of FITS files to decompress '
                             '(e.g. *001[5-9]*.fits.fz or /path/to/*.fits.fz)')
    parser.add_argument('-d', '--data_dir', type=str, default=None, 
                        help='Directory to save files (default: same as input)')
    parser.add_argument('--crop', type=int, nargs=3, metavar=('center_x', 'center_y', 'width'),
                        help='Crop the image data to the specified pixel range')

    args = parser.parse_args()

    # Collect all files (handles both quoted pattern and shell-expanded globs)
    fits_files = []
    for pattern in args.files:
        matched = glob.glob(pattern)
        if matched:
            fits_files.extend(matched)
        else:
            print(f"Warning: No files matched pattern '{pattern}'", file=sys.stderr)

    if not fits_files:
        print("No files found matching the pattern(s).", file=sys.stderr)
        sys.exit(1)
        
        
    fits_files = sorted(set(fits_files))  # remove duplicates if any, and sort

    # Determine output directory
    # Use the directory of the first file if --data_dir not given
    first_dir = os.path.dirname(fits_files[0]) if fits_files else ''
    out_dir = args.data_dir if args.data_dir else first_dir or os.getcwd()
    
    os.makedirs(out_dir, exist_ok=True)

    print(f"Found {len(fits_files)} file(s) to process.")
    
    for f in fits_files:
        print(f"Processing file: {f}")
        data_dir = os.path.dirname(f)
        hdulist = fits.open(f)

        if args.crop:
            center_x, center_y, width = args.crop
            half_width = width // 2
            
            x_start = max(center_x - half_width, 0)
            x_end = center_x + half_width
            y_start = max(center_y - half_width, 0)
            y_end = center_y + half_width
            
            hdulist[0].data = hdulist[0].data[:, y_start:y_end, x_start:x_end]

        out_filename = os.path.join(out_dir, os.path.basename(f))
        hdulist.writeto(out_filename, overwrite=True)
        hdulist.close()
        print(f"Written cropped file to: {out_filename}")
        # Copy telemetry file
        tel_file = os.path.basename(f).replace('.fits', '.txt')
        out_tel_filename = os.path.join(out_dir, tel_file)
        os.system(f'cp {os.path.join(data_dir, tel_file)} {out_tel_filename}')
        print(f"Copied telemetry file to: {out_tel_filename}")