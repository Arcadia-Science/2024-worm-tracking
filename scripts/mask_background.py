import sys
import numpy as np
import skimage
import tifffile
from tqdm import tqdm
from pathlib import Path
import click


DILATION_FACTOR = 30



def make_background_mask_from_standard_deviation(image_stack, ind=None):
    """
    Create a binary mask of the background based on the standard deviation of the image.
    This is used to estimate a mask that will then be refined.
    """
    if image_stack.ndim < 3:
        raise ValueError("Input image must have at least 3 dimensions.")

    subsample_by = 3
    window = 30
    if ind is not None:
        image_stack = image_stack[max(0, ind - window) : min(ind + window, len(image_stack)), :, :]
        subsample_by = 1

    std = image_stack[::subsample_by, :, :].std(axis=0)
    thresh = skimage.filters.threshold_otsu(std)
    mask = std > thresh
    return std, mask


def remove_artifacts(frame, min_area=7000, eccentricity_thresh=0.75):
    """
    Remove small circular artifacts from the image.
    These artifacts exist from discolorations/streaks in the background after initial masking.
    Most of these artifacts end up being circular because of the dilation factor that pads the region of interst.
    The regions are small, so the padding ends up being circular.
    We take advantage of these two properties to try and filter this noise out.

    Parameters:
    - frame: input image frame as a 2D numpy array.
    - min_area: minimum area of objects to keep.
    - eccentricity_thresh: maximum eccentricity to filter out circular shapes.
    
    Returns:
    - cleaned_frame: frame after removing small circular artifacts.
    """
    # Label all connected components in the image
    labeled_frame = skimage.measure.label(frame)
    # Measure properties of labeled regions
    regions = skimage.measure.regionprops(labeled_frame)
    for region in regions:
        # Remove small objects and circular shapes (low eccentricity means more circular)
        if region.area < min_area or region.eccentricity < eccentricity_thresh:
            for coordinates in region.coords:
                labeled_frame[coordinates[0], coordinates[1]] = 0  # Set to background

    # Generate cleaned frame by keeping only the regions that meet criteria
    cleaned_frame = skimage.morphology.remove_small_objects(labeled_frame, min_size=min_area)
    return cleaned_frame 


def apply_background_mask(image_stack):
    """
    Applies background masking to each frame of the image stack and scales the output.
    """
    
    _, estimated_background_mask = make_background_mask_from_standard_deviation(image_stack, ind=None)
    masked_stack = []
    for frame in tqdm(image_stack):
        dog_filtered = skimage.filters.difference_of_gaussians(frame, low_sigma=1, high_sigma=3)
        # A built-in skimage filter to find edges seems to work the best.
        # Reference: https://scikit-image.org/docs/stable/auto_examples/edges/plot_ridge_filter.html#ridge-operators.
        edges = skimage.filters.sato(dog_filtered, sigmas=[0.3, 1], black_ridges=True)

        # Find a threshold for the edges using Otsu's method and the estimated background mask.
        thresh = skimage.filters.threshold_otsu(edges[estimated_background_mask])
        mask = edges > thresh

        # Apply dilation to the mask.
        # This makes sure the worm is buffered and we don't loose parts of it, such as the head.
        selem = skimage.morphology.disk(DILATION_FACTOR)
        dilated_mask = skimage.morphology.dilation(mask, selem)

        # Remove small, circular-ish artifacts from dark spots in the background/agar
        cleaned_mask = remove_artifacts(dilated_mask)

        # Set masked areas to white in the original frame.
        # This should work well with Tierpsy tracker expecting a light background.
        # It also keeps the outline of the worm.
        # I think Tierpsy tracker users the outline to determine head/tail, so this important to keep.
        inverted_mask = np.logical_not(dilated_mask)
        max_intensity = np.max(frame)  # Maximum intensity based on the image type
        subtracted_image = frame.copy()
        subtracted_image[inverted_mask] = max_intensity

        subtracted_image = skimage.exposure.rescale_intensity(subtracted_image, in_range='image', out_range=(0, 1))
        subtracted_image = skimage.util.img_as_ubyte(subtracted_image)
        masked_stack.append(subtracted_image)
    return np.stack(masked_stack)

def process_image(tiff_path: Path, output_path: Path):
    """
    Loads a TIFF stack, applies background masking, and saves the result.
    """
    image_stack = tifffile.imread(str(tiff_path))
    print("Loaded image stack with shape:", image_stack.shape)
    filtered_stack = apply_background_mask(image_stack)
    tifffile.imwrite(str(output_path), filtered_stack, photometric='minisblack')
    print(f"Processed TIFF stack saved to {output_path}")

@click.group()
def cli():
    pass

@click.option("--tiff-path", type=Path, help="Path to the input TIFF file")
@click.option("--output-path", type=Path, help="Path to output dog-filtered TIFF file")
@cli.command()
def background_mask_file(tiff_path: Path, output_path: Path):
    """
    Apply a background mask to a single TIFF stack and output as a new TIFF stack.
    If the output path exists, it will be overwritten.
    """
    process_image(tiff_path, output_path)

@click.option("--input-dirpath", type=Path, help="Path to the input directory of TIFF files")
@click.option("--output-dirpath", type=Path, help="Path to the output directory for processed TIFF files")
@cli.command()
def background_mask_dir(input_dirpath: Path, output_dirpath: Path):
    """
    Applies a background masking to all TIFF files in a directory,
    preserving original TIFF files and directory structure.
        
    input_dirpath: Path to the input directory containing TIFF files and/or subdirectories
        containing TIFF files.
    output_dirpath: Path to the output directory in which the DoG filtered files will be saved
        in the same subdirectory structure as the input directory.
    """
    for dirpath, _, filenames in input_dirpath.walk():
        for filename in filenames:
            if filename.endswith(".tiff"):
                tiff_filepath = dirpath / filename
                bgmask_filename = filename.replace(".tiff", "_bgmask.tiff")
                output_filepath = (
                    output_dirpath
                    / dirpath.relative_to(input_dirpath)
                    / bgmask_filename
                )
                if output_filepath.exists():
                    click.echo(f"File {output_filepath} already exists and will be skipped")
                    continue

                output_filepath.parent.mkdir(exist_ok=True, parents=True)
                process_image(tiff_filepath, output_filepath)


if __name__ == "__main__":
    cli()
