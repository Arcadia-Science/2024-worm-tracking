from pathlib import Path


def find_input_files(input_dirpath, input_prefix_to_remove):
    """
    Searches for all files with the `.nd2` suffix in the specified input directory and its
    subdirectories, removes a user-specified prefix from their file paths, and returns the relative
    paths that uniquely identify each file. These relative paths are intended to be used as
    wildcards in a Snakemake workflow.

    Parameters
    ----------
    input_dirpath : str
        The directory path where the input `.nd2` files reside. This can be an absolute or relative
        path (although we have currently only tested relative paths that are in the same directory
        as the Snakefile).

    input_prefix_to_remove : str
        The prefix of the file paths to be removed. This prefix is typically a common directory path
        that does not contribute to the unique identification of the files (ex. raw-data/). Removing
        this prefix allows for the extraction of the unique portion of each file path.

    Returns
    -------
    filepaths : list of Path
        A list of relative file paths, with the specified prefix removed, that uniquely identify
        the `.nd2` files. These paths are used as wildcards in the Snakemake workflow.
    """
    filepaths = []
    for filepaths_with_suffix in Path(input_dirpath).rglob("*.nd2"):
        filepath_root = filepaths_with_suffix.with_suffix("")
        try:
            relative_path = filepath_root.relative_to(input_prefix_to_remove)
            filepaths.append(relative_path)
        except ValueError:
            filepaths.append(filepath_root)
    return filepaths


INPUT_PREFIX = config["input_prefix"]  # prefix of input_dirpath to remove from all input filepaths
FILEPATHS = find_input_files(
    input_dirpath=config["input_dirpath"], input_prefix_to_remove=INPUT_PREFIX
)
OUTPUT_DIRPATH = Path(config["output_dirpath"])


rule convert_nd2_to_tiff:
    input:
        nd2=INPUT_PREFIX + "/{filepath}.nd2",
    output:
        tiff=OUTPUT_DIRPATH / "raw_tiff" / "{filepath}.tiff",
    conda:
        "envs/dev.yml"
    shell:
        """
        python scripts/convert_nd2.py convert-file --nd2-path {input.nd2} --output-path {output.tiff}
        """


rule difference_of_gaussians_filter:
    input:
        rules.convert_nd2_to_tiff.output.tiff,
    output:
        dog=OUTPUT_DIRPATH / "dogfilter_tiff" / "{filepath}.tiff",
    conda:
        "envs/dev.yml"
    shell:
        """
        python scripts/dog_filter.py dog-filter-file \
            --tiff-path {input.tiff} --output-path {output.dog}
        """


rule convert_tiff_to_mov:
    input:
        tiff=rules.difference_of_gaussians_filter.output.dog,
    output:
        mov=OUTPUT_DIRPATH / "dogfilter_mov" / "{filepath}.mov",
    conda:
        "envs/dev.yml"
    shell:
        """
        python scripts/convert_tiff_to_mov.py convert-file \
            --tiff-path {input.tiff} --mov-path {output.mov}
        """


########################################################
## Quality control
########################################################


rule overlay_mov:
    """
    Overlays each frame of the MOV into a single PNG.
    This allows the user to see the full path of all worms in the video by looking at a single PNG.
    This PNG can be used to visually count the number of worms in an field of view and to get a 
    sense of how quickly the worms were moving (given that the image acquisitions are standardized
    to a consistent frame rate and time).
    """
    input:
        mov=rules.convert_tiff_to_mov.output.mov,
    output:
        png=OUTPUT_DIRPATH / "dogfilter_mov_overlay" / "{filepath}.png",
    conda:
        "envs/dev.yml"
    shell:
        """
        python scripts/overlay_mov.py --mov-path {input.mov} --output-path {output.png}
        """


rule all:
    default_target: True


# future rules:
# rule run_tierpsy_tracker:

# rule compare_tierpsy_tracker_mask_to_input:
# rule summarize_tierpsy_tracker_run:
# """
# * Number of worms counted
# * FPS used
# * ...
# """
