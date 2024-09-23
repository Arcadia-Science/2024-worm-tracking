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
            logging.warning(
                f"'{input_prefix_to_remove}' not in path '{filepath_root}'. Path not modified."
            )
            filepaths.append(filepath_root)
    return filepaths


INPUT_PREFIX = config["input_prefix"]  # prefix of input_dirpath to remove from all input filepaths
FILEPATHS = find_input_files(
    input_dirpath=config["input_dirpath"], input_prefix_to_remove=INPUT_PREFIX
)
OUTPUT_DIRPATH = Path(config["output_dirpath"])
CONFIG_FILEPATH = "conf/dogfilter-no-op50-chunks.json"


rule convert_nd2_to_tiff:
    input:
        nd2=INPUT_PREFIX + "/{filepath}.nd2",
    output:
        tiff=temp(OUTPUT_DIRPATH / "raw_tiff" / "{filepath}.tiff"),
    conda:
        "envs/dev.yml"
    shell:
        """
        python scripts/convert_nd2.py convert-file --nd2-path {input.nd2} --output-path {output.tiff}
        """


rule difference_of_gaussians_filter:
    input:
        tiff=rules.convert_nd2_to_tiff.output.tiff,
    output:
        tiff=temp(OUTPUT_DIRPATH / "dogfilter_tiff" / "{filepath}.tiff"),
    conda:
        "envs/dev.yml"
    shell:
        """
        python scripts/dog_filter.py dog-filter-file \
            --tiff-path {input.tiff} --output-path {output.tiff}
        """


rule convert_tiff_to_mov:
    input:
        tiff=rules.difference_of_gaussians_filter.output.tiff,
    output:
        mov=temp(OUTPUT_DIRPATH / "dogfilter_mov" / "{filepath}.mov"),
    conda:
        "envs/dev.yml"
    shell:
        """
        python scripts/convert_tiff_to_mov.py convert-file \
            --tiff-path {input.tiff} --mov-path {output.mov}
        """


rule run_tierpsy_tracker:
    """
    This rule executes the Tierpsy tracker worm motility analysis.
    The recommended way to install and use Tierpsy tracker is in Docker container that runs a GUI.
    However, this approach is difficult to automate.
    We changed the Docker container and launch script so that it runs in the background without
    using the GUI.
    We then send commands to the Docker container from this snakemake rule.
    See the README in this repository for more details on this approach.
    """
    input:
        mov=expand(rules.convert_tiff_to_mov.output.mov, filepath=FILEPATHS),
        config=CONFIG_FILEPATH,
    output:
        hdf5_mask=expand(
            OUTPUT_DIRPATH / "tierpsy_out" / "masks" / "{filepath}.hdf5",
            filepath=FILEPATHS,
        ),
        hdf5_result=expand(
            OUTPUT_DIRPATH / "tierpsy_out" / "results" / "{filepath}_featuresN.hdf5",
            filepath=FILEPATHS,
        ),
    params:
        input_dir=OUTPUT_DIRPATH / "dogfilter_mov",
        mask_dir=OUTPUT_DIRPATH / "tierpsy_out" / "masks",
        results_dir=OUTPUT_DIRPATH / "tierpsy_out" / "results",
    shell:
        """
        docker exec -u root \
            -e SHELL=/bin/bash \
            -e HOME=/home/tierpsy_user \
            -e PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/tierpsy_user/.local/bin \
            -e TERM=xterm \
            -e PWD=/DATA \
            -e SHLVL=1 \
            -e LIBGL_ALWAYS_INDIRECT=1 \
            -e DOCKER_HOME=/home/tierpsy_user \
            -e _=/usr/bin/env \
            my_tierpsy_container \
            /bin/bash -c "umask 000; tierpsy_process --video_dir_root local_drive/{params.input_dir} --json_file local_drive/{input.config} --mask_dir_root local_drive/{params.mask_dir} --pattern_include *.mov --results_dir_root local_drive/{params.results_dir}"
        """


########################################################
## Quality control
########################################################


rule make_projection_from_tiff:
    """
    Projects each frame of the FOV acquisition into a single PNG.
    This allows the user to see the full path of all worms in the video by looking at a single PNG.
    This PNG can be used to visually count the number of worms in an field of view and to get a 
    sense of how quickly the worms were moving (given that the image acquisitions are standardized
    to a consistent frame rate and time).
    """
    input:
        tiff=rules.difference_of_gaussians_filter.output.tiff,
    output:
        png=OUTPUT_DIRPATH / "quality_control" / "dogfilter_projection" / "{filepath}.png",
    conda:
        "envs/dev.yml"
    shell:
        """
        python scripts/make_projection_from_tiff.py --tiff-path {input.tiff} --output-path {output.png}
        """


rule compare_tierpsy_mask_to_input_mov:
    input:
        hdf5=OUTPUT_DIRPATH / "tierpsy_out" / "masks" / "{filepath}.hdf5",
        mov=rules.convert_tiff_to_mov.output.mov,
    output:
        png=OUTPUT_DIRPATH
        / "quality_control"
        / "compare_tierpsy_mask_to_input_mov"
        / "{filepath}.png",
    conda:
        "envs/dev.yml"
    shell:
        """
        python scripts/compare_tierpsy_mask_to_input_mov.py {input.hdf5} {input.mov} {output.png}
        """


rule all:
    default_target: True
    input:
        expand(rules.compare_tierpsy_mask_to_input_mov.output.png, filepath=FILEPATHS),
        expand(rules.make_projection_from_tiff.output.png, filepath=FILEPATHS),
        expand(rules.run_tierpsy_tracker.output.hdf5_result, filepath=FILEPATHS),


# rule summarize_tierpsy_tracker_run:
# """
# * Number of worms counted
# * FPS used
# * ...
# """
