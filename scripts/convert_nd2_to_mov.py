from pathlib import Path

import click
import imageio
import nd2
import numpy as np
from tqdm import tqdm


@click.option("--nd2-path", type=Path, help="Path to the nd2 file")
@click.option("--mov-path", type=Path, help="Path to output mov file")
@click.command()
def main(nd2_path: str, mov_path: str) -> None:
    """
    Converts an ND2 file to a MOV file.

    Args:
        nd2_path (str): Path to the ND2 file.
        mov_path (str): Path to the output MOV file.

    Returns:
        None
    """
    nd2_dask = nd2.imread(nd2_path, dask=True)

    # TER TODO update this to not be hardcoded or to what is final experiment
    fps = 18.5  # Default FPS if not found in metadata

    # Check metadata for frame rate info, if available
    # TER TODO im not sure this is reading the nd2 metadata correctly, check and update
    if (
        hasattr(nd2_dask, "metadata")
        and "experiment" in nd2_dask.metadata
        and "timing" in nd2_dask.metadata["experiment"]
        and "frame_rate" in nd2_dask.metadata["experiment"]["timing"]
    ):
        fps = nd2_dask.metadata["experiment"]["timing"]["frame_rate"]

    writer = imageio.get_writer(str(mov_path), fps=fps, quality=7, format="FFMPEG")

    num_frames = nd2_dask.shape[0]

    print(f"Converting {nd2_path} to {mov_path} with {fps} fps and {num_frames} frames.")

    for frame_idx in tqdm(range(num_frames)):
        frame = np.asarray(nd2_dask[frame_idx])

        if frame.ndim > 2:
            frame = frame[0]

        if frame.ndim == 2:
            writer.append_data(frame)
        else:
            print(f"Skipped frame {frame_idx} due to incorrect dimensions.")

    writer.close()


if __name__ == "__main__":
    main()
