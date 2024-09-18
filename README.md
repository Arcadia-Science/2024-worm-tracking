# Analyzing *C. elegans* motility phenotypes with Tierpsy tracker 

[![run with conda](http://img.shields.io/badge/run%20with-conda-3EB049?labelColor=000000&logo=anaconda)](https://docs.conda.io/projects/miniconda/en/latest/)

## Purpose

This repository implements an automated approach for analyzing worm motility phenotypes.
This pipeline is designed to assess worm motility phenotypes from images captured on an upright widefield microscope.
Our images have the following profile:
* 30 second acquitions
* 24.5 frames per second
* 2x field of view
* worms plated on agar without a bacterial lawn (OP50).

The image analysis pipeline produces statistical estimates of motility phenotype differences between two strains (typically wildtype and mutant).

## Installation and Setup

This repository primarily uses conda to manage software environments and installations. You can find operating system-specific instructions for installing miniconda [here](https://docs.conda.io/projects/miniconda/en/latest/). After installing conda and [mamba](https://mamba.readthedocs.io/en/latest/), run the following command to create the pipeline run environment.

```{bash}
mamba env create -n wormmotility --file envs/dev.yml
conda activate wormmotility
```

In addition, the tool [Tierpsy tracker](https://github.com/Tierpsy/tierpsy-tracker/blob/development/docs/INSTALLATION_DOCKER.md) recommends/requires installation via Docker.
Because of the way the Docker container is configured, we had trouble running it with Singularity inside of snakemake (see this [issue](https://github.com/Arcadia-Science/2024-worm-tracking/issues/4)).
We came up with a workaround where the Docker container is started and run in the background and then commands are executed in the Docker container by Snakemake.
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
    --config input_dirpath=/home/theia/arc_nas/Babu_frik/Justin/2024-08-20/N2_pl1 input_prefix=/home/theia/arc_nas/Babu_frik/Justin output_dirpath=outputs
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

TODO: Add details about the description of input / output data and links to Zenodo depositions, if applicable.

## Overview

### Description of the folder structure

### Methods

TODO: Include a brief, step-wise overview of analyses performed.

> Example:
>
> 1.  Download scripts using `download.ipynb`.
> 2.  Preprocess using `./preprocessing.sh -a data/`
> 3.  Run Snakemake pipeline `snakemake --snakefile Snakefile`
> 4.  Generate figures using `pub/make_figures.ipynb`.

### Compute Specifications

TODO: Describe what compute resources were used to run the analysis. For example, you could list the operating system, number of cores, RAM, and storage space.

## Contributing

See how we recognize [feedback and contributions to our code](https://github.com/Arcadia-Science/arcadia-software-handbook/blob/main/guides-and-standards/guide-credit-for-contributions.md).
