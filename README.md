# Analyzing *C. elegans* motility phenotypes with Tierpsy tracker

[![run with conda](http://img.shields.io/badge/run%20with-conda-3EB049?labelColor=000000&logo=anaconda)](https://docs.conda.io/projects/miniconda/en/latest/)

## Purpose

This repository implements an automated approach for analyzing worm motility phenotypes.
This pipeline is designed to assess worm motility phenotypes from images captured on an upright wide field microscope.
Our images have the following profile:

* 30 second acquisitions
* 24.5 frames per second
* Field of view:
    * 1976 x 1976 pixels
    * 1.625 microns per pixel
* Worms plated on agar without a bacterial lawn (OP50).

The image analysis pipeline produces statistical estimates of motility phenotype differences between two strains (typically wild type and mutant).

## Installation and Setup

This repository primarily uses conda to manage software environments and installations.
You can find operating system-specific instructions for installing miniconda [here](https://docs.conda.io/projects/miniconda/en/latest/).
After installing conda and [mamba](https://mamba.readthedocs.io/en/latest/), run the following command to create the pipeline run environment.

```{bash}
mamba env create -n wormmotility --file envs/dev.yml
conda activate wormmotility
```

In addition, the tool [Tierpsy tracker](https://github.com/Tierpsy/tierpsy-tracker/blob/development/docs/INSTALLATION_DOCKER.md) recommends/requires installation via Docker.
Because of the way the Docker container is configured, we had trouble running it with Singularity inside of snakemake (see this [issue](https://github.com/Arcadia-Science/2024-worm-tracking/issues/4)).
We came up with a workaround where the Docker container runs in the background and then commands are executed in the Docker container by Snakemake.
This requires starting the Docker container before running the pipeline.
This is a sub-par solution, but we decided this was the best approach given time and bandwidth limitations.

To enable Tierpsy tracker execution within the Docker container and via snakemake, start by installing Docker Desktop according to your operating system.
(Linux Ubuntu instructions are available [here](https://docs.docker.com/desktop/install/linux/ubuntu/)).
Also note that even when installed via Docker, Tierpsy tracker will not work on Mac computers with ARM-based processors (Apple silicon, M* chips).
Once Docker is installed, you may need to adjust user permissions to allow Docker to run without invoking `sudo` privileges for every command.
We used the following commands to configure Docker for this.

```{bash}
# Check if you're in the Docker group. Among other words, this should print docker
groups

# If the above doesn't say docker, add user to docker group
sudo usermod -aG docker $USER

# Export docker host to env variable
export DOCKER_HOST=unix:///var/run/docker.sock
```

Once configured, start Docker.
This command will need sudo privileges still.
```{bash}
sudo systemctl start docker
```

Once Docker is started, pull the Tierpsy tracker Docker container.
We provide a modified Docker container that does not launch the graphical user interface upon launch.
```{bash}
docker pull arcadiascience/tierpsy-tracker-no-gui:fc691a090d8a
```

Then, start a non-interactive session where the Docker container will run in the background.
```{bash}
bash scripts/tierpsy_linux_no_gui_background.sh
```

Check that the container is running using the command below.
There should be a row in the returned table with the name `my_tierpsy_container`.
```{bash}
docker ps
```

We're now ready to execute the pipeline using Snakemake.
Snakemake itself is installed in the main development conda environment as specified in the [dev.yml](./envs/dev.yml) file.

To start the pipeline, run:

```{bash}
snakemake -j 1 \
    --software-deployment-method conda \
    --rerun-incomplete \
    --config input_dirpath=/path/to/raw/dataset/dir input_prefix=/prefix/to/remove/from/input_dirpath output_dirpath=outputs
```

Where:

* `-j`: designates the number of cores used by Snakemake to parallelize rules.
* `--software-deployment-method`: tells Snakemake to launch each rule in a conda environment where specified.
* `--rerun-incomplete`: tells Snakemake to check that all file are completely written and to re-run those that are not.
* `--config`: feeds pipeline-specific configuration parameters to snakemake.
    * `input_dirpath`: The directory where input files are located. If files are located in subdirectories, this is the root filepath for all directories to be analyzed by the snakemake run.
    * `input_prefix`: Portion of `input_dirpath` to omit from output file names. A file's absolute path is used as the identifier by this pipeline. When an `input_prefix` is supplied, the prefix will be removed from the output filepath (so instead of having `/home/theia/arc_nas/Babu_frik/Justin` in every output file path, this prefix would be removed). This removes non-identifying information from the output filepaths so that they directory structure doesn't become unnecessarily deep.
    * `output_dirpath`: Directory path to write output files.

## Data

This pipeline is designed to run on videos (time series of images collected from a single field of view) of live adult *C. elegans*.
Importantly, the videos should have a relatively homogenous background (i.e., little variation in intensity or contrast).
It takes raw image files (in Nikon's ND2 format) as input and outputs motility phenotypes for the worms, statistical analysis comparing strains, and quality control reports.
All analyzed data are currently available on the NAS (TODO: update to public data location).

## Overview

This repository implements a simple workflow to estimate and compare worm motility phenotypes.
It is centered around [Tierpsy tracker](https://github.com/Tierpsy/tierpsy-tracker/tree/development), a method that processes and tracks worms and produces motility data for those worms ([publication](https://royalsocietypublishing.org/doi/10.1098/rstb.2017.0375)).
The pipeline uses the per-worm, per-frame time series motility estimates to generate simple features (ex. mean length, mean speed, mean tail speed, etc.) that are then compared between strains.

### Description of the folder structure

#### Folders and files in this repository

* [conf/](./conf/): Configuration files for the tools executed by the pipeline, mainly Tierpsy tracker.
* [docker/](./docker): Tierpsy tracker needs to be installed by Docker. We provide a Dockerfile documenting changes we made to the Tierpsy tracker image to allow the image to start without a GUI.
* [envs/](./envs): This repository uses conda to manage software installations and versions. Other than Tierpsy tracker, all software installations are managed by environment files in this directory.
* [scripts/](./scripts): Python, R and bash scripts used by the Snakefile in this repository.
* [`LICENSE`](./LICENSE): License specifying the re-use terms for the code in this repository.
* [`README.md`](./README.md): File outlining the contents of this repository and how to use the image analysis pipeline.
* [`Snakefile`](./Snakefile): The snakemake workflow file that orchestrates the full image analysis pipeline.
* [.github/](./.github), [.vscode/](./.vscode), [.gitignore](./.gitignore), [.pre-commit-config.yaml](./.pre-commit-config.yaml), [Makefile](./Makefile), [pyproject.toml](./Makefile): Files that control the development environment of the repository.

#### Folders and files output by the workflow

In the user-specified output directory, snakemake creates the following intermediate folders:
`dogfilter_mov/`, `dogfilter_projection/`, and `dogfilter_tiff/`.

The Tierpsy tracker results are in the folder `tierpsy_out/`.
The HDF5 files in the `masks` directory are intermediate files that record a mask that shows which worms are tracked.
These files are used by the quality control portion of the pipeline.
The HDF5 files in the `results` directory record the motility information for worms.
See the Tierpsy tracker [documentation](https://github.com/Tierpsy/tierpsy-tracker/blob/development/docs/OUTPUTS.md) for more information about these outputs.

### Methods

The Snakemake file in this repository orchestrates the analysis of raw time series images (videos) for extracting and comparing motility phenotypes between strains of *C. elegans*.
The pipeline follows the following steps.

**Motility analysis and comparison**:

1. Convert raw images from Nikon's ND2 format to TIFF format.
2. Apply a difference of gaussian (DoG) filter to the TIFF images. This detects differences between the background and foreground. It retains the foreground (the worms) while masking out the background.
3. Convert the TIFF image series to MOV files, as MOV is the format required by Tierpsy tracker.
4. Run the Tierpsy tracker analysis to produce motility estimates for each worm.
5. Process the Tierpsy tracker raw motility estimates and perform statistical analysis to compare strains.

**Quality control**:

1. Make a projection from the DoG-filtered TIFF. This creates a summary PNG where all TIFF files from a single time series are overlaid, so that all movement of the worms over the 30 second acquisition is summarized in a single image.
2. TODO: Compare the Tierpsy tracker mask to the raw image for a single frame.
3. TODO: Produce summary stats for each field of view.

### Compute Specifications

We executed this pipeline on a Linux Ubuntu machine.
While the machine has 64 cores and 503 GB RAM, we ran the pipeline on a single core using a small fraction of the available RAM.
While many of the components of the pipeline would be run on a Mac with an Intel chip, we have tailored the pipeline for Ubuntu (Tierpsy tracker installation and launch).

## Contributing

See how we recognize [feedback and contributions to our code](https://github.com/Arcadia-Science/arcadia-software-handbook/blob/main/guides-and-standards/guide-credit-for-contributions.md).
