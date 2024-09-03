import pathlib

import click
import matplotlib.pyplot as plt
import numpy as np
import skimage
import tifffile


@click.command()
@click.option("--tiff-path", type=click.Path(exists=True), required=True, help="Path to TIFF file.")
@click.option("--output-path", type=click.Path(), required=True, help="Path to output PNG file.")
def make_projection_from_tiff(tiff_path, output_path):
    """
    Overlay all frames in a TIFF file and save the resulting image as a PNG.
    """
    tiff_file_path = pathlib.Path(tiff_path).absolute()

    # Read the TIFF file
    images = tifffile.imread(str(tiff_file_path))

    if images.ndim == 2:  # Single frame in TIFF
        images = images[np.newaxis, ...]

    # Create min-intensity projection across all frames
    min_proj = np.min(images, axis=0)

    # Scale the image to uint8
    scaled_image = skimage.util.img_as_ubyte(min_proj)

    # Save the output image
    output_file_path = pathlib.Path(output_path).absolute()
    plt.imsave(output_file_path, scaled_image, cmap="gray")

    click.echo(f"Overlay image saved as {output_file_path}")


if __name__ == "__main__":
    make_projection_from_tiff()
