import shutil
from pathlib import Path

import click
import imageio
import nd2
import numcodecs
import numpy as np
import tifffile
import zarr
from tqdm import tqdm

XY_DOWNSAMPLE_FACTOR = 2
T_DOWNSAMPLE_FACTOR = 2


@click.group()
def cli():
    pass


@click.option("--nd2-path", type=Path, help="Path to the nd2 file")
@click.option("--output-path", type=Path, help="Path to the output file")
@cli.command()
def convert_file(nd2_path: Path, output_path: Path) -> None:
    _convert_file(nd2_path, output_path)


def _convert_file(nd2_path: Path, output_path: Path) -> None:
    """
    Convert a single ND2 file to the format corresponding to the file extension of the output path.

    If the output path exists, it will be overwritten.
    """
    raw_image = nd2.imread(nd2_path, dask=True)

    # The raw image has dimensions (T, X, Y).
    raw_image = np.asarray(raw_image)[
        ::T_DOWNSAMPLE_FACTOR, ::XY_DOWNSAMPLE_FACTOR, ::XY_DOWNSAMPLE_FACTOR
    ]

    file_format = output_path.suffix[1:].lower()
    if file_format == "mov":
        # We use an arbitrary FPS of 10 that is suitable for visual inspection.
        with imageio.get_writer(str(output_path), fps=10, quality=7, format="FFMPEG") as writer:
            num_frames = raw_image.shape[0]
            for frame_idx in tqdm(range(num_frames)):
                frame = np.asarray(raw_image[frame_idx])
                if frame.ndim != 2:
                    raise ValueError(f"Frame {frame_idx} has incorrect dimensions.")
                writer.append_data(frame)

    elif file_format == "tiff":
        tifffile.imwrite(output_path, raw_image)

    elif file_format == "zarr":
        # Zarr "files" are actually directories, so we need to delete the existing directory
        # and create a new one before saving the zarr array.
        shutil.rmtree(output_path, ignore_errors=True)
        output_path.mkdir(exist_ok=True, parents=True)

        xy_size = raw_image.shape[1]
        zarr_array = zarr.array(
            raw_image,
            compressor=zarr.Blosc(cname="zstd", clevel=3, shuffle=numcodecs.Blosc.BITSHUFFLE),
            # We use a chunksize that spans multiple frames in an attempt to optimize
            # the compression ratio (since adjacent frames are highly correlated).
            chunks=(10, xy_size, xy_size),
        )
        click.echo(zarr_array.info)
        zarr.save(str(output_path), zarr_array)

    else:
        raise ValueError(f"Unsupported file format: {file_format}")

    click.echo(f"Converted {nd2_path} to {output_path}.")


@click.option("--input-dirpath", type=Path, help="Path to the input directory")
@click.option("--output-dirpath", type=Path, help="Path to the output directory")
@click.option("--file-format", type=str, help="Output file format", default="tiff")
@cli.command()
def convert_dir(input_dirpath: Path, output_dirpath: Path, file_format: str) -> None:
    """
    Converts all ND2 files in a directory, preserving its directory structure.

    input_dirpath: Path to the input directory containing ND2 files
        and/or subdirectories containing ND2 files.
    output_dirpath: Path to the output directory in which the converted files will be saved
        in the same subdirectory structure as the input directory.
    file_format: Output file format.
    """
    for dirpath, _, filenames in input_dirpath.walk():
        for filename in filenames:
            if filename.endswith(".nd2"):
                nd2_filepath = dirpath / filename
                output_filepath = (
                    output_dirpath
                    / dirpath.relative_to(input_dirpath)
                    / nd2_filepath.with_suffix(f".{file_format}").name
                )
                if output_filepath.exists():
                    click.echo(f"File {output_filepath} already exists and will be skipped")
                    continue

                output_filepath.parent.mkdir(exist_ok=True, parents=True)
                _convert_file(nd2_filepath, output_filepath)


if __name__ == "__main__":
    cli()
