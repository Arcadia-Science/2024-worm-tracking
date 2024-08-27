

rule convert_nd2_to_tiff:
    input: nd2 = 
    output: tiff = 
    conda: "envs/dev.yml"
    shell:
        """
        python scripts/convert_nd2.py convert-file --nd2-path {input.nd2} --output-path {output.tiff}
        """

rule difference_of_gaussians_filter:
    input: rules.convert_nd2_to_tiff.output.tiff
    output: dog = 
    conda: "envs/dev.yml"
    shell:
        """
        python scripts/dog_filter.py dog-filter-file \
            --tiff-path {input.tiff} --output-path {output.dog}
        """

rule convert_tiff_to_mov:
    input: tiff = rules.difference_of_gaussians_filter.output.dog
    output: mov = 
    conda: "envs/dev.yml"
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
    input: mov = rules.convert_tiff_to_mov.output.mov
    output: png = 
    conda: "envs/dev.yml"
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
"""
* Number of worms counted
* FPS used
* ...
"""
