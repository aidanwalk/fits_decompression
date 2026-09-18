"""
Decompress ARCHIVED fits data and return the filenames to a pre-archived like 
state. For example, the file name will be generated from the obs-time in the 
fits header. 

"""
import os
import glob
import sys
from astropy.io import fits


def read_fits_file(filename):
    """Open a .fits file.
       Return the hdulist
    """

    # Open the file
    try:
        return fits.open(filename)

    except IOError as e:
        print(f"Could not read file {filename}: {e}", file=sys.stderr)
        sys.exit(1)


def write_fits_file(hdulist, filename='out.fits'):
    """Create a new fits object from data and headers, and write to file."""
    
    # Write to file
    hdulist.writeto(filename, overwrite=True)
    hdulist.close()


def decompress_fits(hdulist):
    new_hdulist = [hdulist[0]]
    
    for h in hdulist[1:]:
        new_hdu = fits.ImageHDU(h.data, header=h.header)
        
        new_hdulist.append(new_hdu)
        
    return fits.HDUList(new_hdulist)
    
    
def compress_fits(hdulist):
    new_hdulist = []
    
    for h in hdulist:
        if type(h) == fits.PrimaryHDU:
            if h.data is not None:
                new_hdulist.append(fits.PrimaryHDU(None, header=h.header))
                new_hdulist.append(fits.CompImageHDU(h.data, header=h.header))
            else:
                new_hdulist.append(h)
        
        elif type(h) == fits.ImageHDU:
            new_hdu = fits.CompImageHDU(h.data, header=h.header)
            new_hdulist.append(new_hdu)
        else:
            new_hdulist.append(h)
        
    return fits.HDUList(new_hdulist)
    
    
    
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Decompress fits files.')
    parser.add_argument('files', nargs='+',  # <-- This is the key change
                        help='Glob pattern or list of FITS files to decompress '
                             '(e.g. *001[5-9]*.fits.fz or /path/to/*.fits.fz)')
    parser.add_argument('-p', '--prepend', type=str, default='', 
                        help='String to prepend to output filenames')
    parser.add_argument('-d', '--data_dir', type=str, default=None, 
                        help='Directory to save decompressed files (default: same as input)')
    parser.add_argument('--crop', type=int, nargs=3, metavar=('center_x', 'center_y', 'width'),
                        help='Crop the image data to the specified pixel range')
    parser.add_argument('--detector', type=str, default=None,
                        help='Specify the detector used for the FITS files, e.g. "VCAM1 - OrcaQ   "')

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

    print(f"Found {len(fits_files)} file(s) to decompress.")

    for f in fits_files:
        
        # If a detector is specified, check the header for the detector information
        if args.detector:
            hdr = fits.getheader(f, ext=1)
            detector_in_header = hdr["DETECTOR"]
            if args.detector not in detector_in_header:
                print(f"Detector mismatch for file {f}. Expected '{args.detector}', found '{detector_in_header}', skipping")
                print("\n\n")
                continue

        print(f"Decompressing file: {f}")
        data_dir = os.path.dirname(f)
        hdulist = read_fits_file(f)
        
        
        
        new_hdulist = decompress_fits(hdulist)
        
        assert len(new_hdulist) == 2, "Unexpected number of HDUs in decompressed file."
        # Get rid of the first HDU since it is empty
        assert new_hdulist[0].data is None, "First HDU is not empty as expected."
        
        # Crop the data if requested
        if args.crop:
            center_x, center_y, width = args.crop
            half_width = width // 2
            
            x_start = max(center_x - half_width, 0)
            x_end = center_x + half_width
            y_start = max(center_y - half_width, 0)
            y_end = center_y + half_width
            
            new_hdulist[1].data = new_hdulist[1].data[:, y_start:y_end, x_start:x_end]
        
        # data = np.mean(new_hdulist[1].data, axis=0)
        # new_hdulist = fits.HDUList(fits.PrimaryHDU(data, header=new_hdulist[1].header))
        new_hdulist = fits.HDUList(fits.PrimaryHDU(new_hdulist[1].data, header=new_hdulist[1].header))
            
        print(len(new_hdulist), "HDUs in decompressed file.")
        
        # Create the new filename from the header info
        obs_time = new_hdulist[-1].header['UT-END']
        
        if obs_time.startswith('_') and args.prepend == '':
            obs_time = obs_time[1:]
        elif not obs_time.startswith('_') and args.prepend != '': 
            obs_time = '_' + obs_time
        # obs_time = obs_time.replace(':', '_')
        out_filename = os.path.join(out_dir, f'{args.prepend}{obs_time}.fits')
        
        tel_file = os.path.basename(f).replace('.fits.fz', '.txt')
        out_tel_filename = os.path.join(out_dir, f'{args.prepend}{obs_time}.txt')
        os.system(f'echo cp {os.path.join(data_dir, tel_file)} {out_tel_filename}')
        os.system(f'cp {os.path.join(data_dir, tel_file)} {out_tel_filename}')
        print("Copied telemetry file to:", out_tel_filename)
        
        write_fits_file(new_hdulist, filename=out_filename)
        print("Written decompressed file to:", out_filename)
        print()
        