import os
import click
import imageio
from pathlib import Path
import tifffile as tiff
from tqdm import tqdm

@click.group()
def cli():
    pass

def _convert_file(tiff_path: Path, mov_path: Path) -> None:
    """
    Convert a single TIFF file to MOV format.
    """
    tiff_stack = tiff.imread(tiff_path)
    frames = [frame for frame in tqdm(tiff_stack, desc="Processing frames")]

    with imageio.get_writer(str(mov_path), fps=24.5, codec='libx264', quality=8) as writer:
        for frame in tqdm(frames, desc="Writing frames to video"):
            writer.append_data(frame)
    click.echo(f"Converted {tiff_path} to {mov_path}.")

@click.option("--tiff-path", type=Path, help="Path to the input TIFF file")
@click.option("--mov-path", type=Path, help="Path to output MOV file")
@cli.command()
def convert_file(tiff_path: Path, mov_path: Path) -> None:
    """
    Command line interface to convert a single TIFF file to MOV format.
    """
    if mov_path.exists():
        click.echo(f"File {mov_path} already exists and will be skipped.")
        return
    mov_path.parent.mkdir(parents=True, exist_ok=True)
    _convert_file(tiff_path, mov_path)

@click.option("--input-dirpath", type=Path, help="Path to the input directory containing TIFF files")
@click.option("--output-dirpath", type=Path, help="Path to the output directory for MOV files")
@click.option("--filter-string", default="dogfilter", help="Filter string to select files for conversion")
@cli.command()
def convert_dir(input_dirpath: Path, output_dirpath: Path, filter_string: str) -> None:
    """
    Converts all TIFF files in a directory to MOV format, preserving its directory structure.
    Only files containing the specified filter string in their filenames are converted.
    """
    for dirpath, _, filenames in os.walk(input_dirpath):
        dirpath = Path(dirpath)
        for filename in filenames:
            if filename.endswith(".tiff") and filter_string in filename:
                tiff_path = dirpath / filename
                relative_path = tiff_path.relative_to(input_dirpath)
                mov_path = output_dirpath / relative_path.with_suffix('.mov')
                if mov_path.exists():
                    click.echo(f"File {mov_path} already exists and will be skipped")
                    continue

                mov_path.parent.mkdir(parents=True, exist_ok=True)
                _convert_file(tiff_path, mov_path)

if __name__ == "__main__":
    cli()
