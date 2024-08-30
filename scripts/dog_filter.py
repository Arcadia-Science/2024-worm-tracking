from pathlib import Path

import click
import numpy as np
import skimage.exposure
import skimage.filters
import skimage.util
import tifffile
from tqdm import tqdm


def apply_dog_filter(image_stack):
    """
    Applies the Difference of Gaussian (DoG) filter to each frame of the image stack and scales the
    output.
    """
    filtered_stack = []
    for frame in tqdm(image_stack):
        dog_filtered = skimage.filters.difference_of_gaussians(frame, low_sigma=0.3, high_sigma=3)
        dog_filtered = skimage.exposure.rescale_intensity(
            dog_filtered, in_range="image", out_range=(0, 1)
        )
        dog_filtered = skimage.util.img_as_ubyte(dog_filtered)
        filtered_stack.append(dog_filtered)
    return np.stack(filtered_stack)


def process_image(tiff_path: Path, output_path: Path):
    """
    Loads a TIFF stack, processes it using the DoG filter, and saves the result.
    """
    image_stack = tifffile.imread(str(tiff_path))
    print("Loaded image stack with shape:", image_stack.shape)
    filtered_stack = apply_dog_filter(image_stack)
    tifffile.imwrite(str(output_path), filtered_stack, photometric="minisblack")
    print(f"Processed TIFF stack saved to {output_path}")


@click.group()
def cli():
    pass


@click.option("--tiff-path", type=Path, help="Path to the input TIFF file")
@click.option("--output-path", type=Path, help="Path to output dog-filtered TIFF file")
@cli.command()
def dog_filter_file(tiff_path: Path, output_path: Path):
    """
    Apply a DoG filter to a single TIFF stack and output as a new TIFF stack.
    If the output path exists, it will be overwritten.
    """
    process_image(tiff_path, output_path)


@click.option("--input-dirpath", type=Path, help="Path to the input directory of TIFF files")
@click.option(
    "--output-dirpath", type=Path, help="Path to the output directory for processed TIFF files"
)
@cli.command()
def dog_filter_dir(input_dirpath: Path, output_dirpath: Path):
    """
    Applies a DoG filter to all TIFF files in a directory, preserving original TIFF files and
    directory structure.

    input_dirpath: Path to the input directory containing TIFF files and/or subdirectories
        containing TIFF files.
    output_dirpath: Path to the output directory in which the DoG filtered files will be saved
        in the same subdirectory structure as the input directory.
    """
    for dirpath, _, filenames in input_dirpath.walk():
        for filename in filenames:
            if filename.endswith(".tiff"):
                tiff_filepath = dirpath / filename
                dog_filter_filename = filename.replace(".tiff", "_dogfilter.tiff")
                output_filepath = (
                    output_dirpath / dirpath.relative_to(input_dirpath) / dog_filter_filename
                )
                if output_filepath.exists():
                    click.echo(f"File {output_filepath} already exists and will be skipped")
                    continue

                output_filepath.parent.mkdir(exist_ok=True, parents=True)
                process_image(tiff_filepath, output_filepath)


if __name__ == "__main__":
    cli()
