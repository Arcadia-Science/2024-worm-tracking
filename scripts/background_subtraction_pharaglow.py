#!/usr/bin/env python

"""background_subtraction.py: Script for background subtraction in worm motility videos."""

import argparse

import imageio.v3 as iio
import numpy as np
import pims
import skimage.io as io
from skimage import filters, morphology, util


@pims.pipeline
def subtract_background(image, background):
    """
    Subtract a background from the image. This function re-scales the image data to ensure all pixel
    values lie between 0 and 1, making the data uniform in scale and often improving the
    effectiveness of subsequent processing operations like thresholding, segmentation, and feature
    extraction. This normalization is particularly useful when the input images can have different
    lighting conditions or contrast levels, ensuring that the processing steps that follow are not
    biased by these variations.

    Args:
        image (numpy.array or pims.Frame): input image
        background (numpy.array or pims.Frame): second image with background

    Returns:
        numpy.array: background subtracted image
    """
    tmp = image - background
    minimum, maximum = np.min(tmp), np.max(tmp)
    # adjusts the pixel values such that the lowest value becomes zero
    tmp -= minimum
    # scales the adjusted pixel values to a normalized range between 0 and 1
    tmp /= (maximum - minimum)
    return util.img_as_float(tmp)

@pims.pipeline
def preprocess(image, smooth=0, threshold=None, dilate=False):
    """
    Apply image processing functions to return a binary image.

    Args:
        img (numpy.array or pims.Frame): input image
        smooth (int): apply a gaussian filter to img with width=smooth
        threshold (float): threshold value to apply after smoothing (default: None)
        dilate (int): apply a binary dilation n = dilate times (default = False)

    Returns:
        numpy.array: binary (masked) image
    """
    if smooth:
        image = filters.gaussian(image, smooth, preserve_range=True)
    if threshold is None:
        threshold = filters.threshold_yen(image)
    mask = image >= threshold
    for _ in range(dilate):
        mask = morphology.dilation(mask)
    return mask

def calculate_background(frames, background_window=30):
    """
    Calculate the background image using a median stack projection.

    Args:
        frames (numpy.array or pims.ImageSequence): image stack with input images
        background_window (int): subsample frames for background creation by selecting
            background_window numbers of frames evenly spaced. Defaults to 30.

    Returns:
        numpy.array: background image
    """
    select_frames = np.linspace(0, len(frames) - 1, background_window).astype(int)
    background = np.median(frames[select_frames], axis=0)
    return background

def process_video(input_file, output_file, background_window, smooth, apply_threshold):
    frames = io.imread(input_file)
    background = calculate_background(frames, background_window)
    subtracted_frames = [subtract_background(frame, background) for frame in frames]

    if smooth:
        subtracted_frames = [
            filters.gaussian(frame, smooth, preserve_range=True) for frame in subtracted_frames
        ]

    if apply_threshold:
        thresholded_frames = [
            preprocess(frame, smooth, threshold=filters.threshold_yen(frame))
            for frame in subtracted_frames
        ]
        processed_frames = [util.img_as_ubyte(frame) for frame in thresholded_frames]
    else:
        processed_frames = [util.img_as_ubyte(frame) for frame in subtracted_frames]

    fps = iio.immeta(input_file)['fps']
    iio.imwrite(output_file, processed_frames, fps=fps)

def main():
    parser = argparse.ArgumentParser(description="Background subtraction for worm motility videos.")
    parser.add_argument("input_file", type=str, help="Path to the input video file in mov format.")
    parser.add_argument(
        "output_file",
        type=str,
        help="Path to the output video file.",
    )
    parser.add_argument(
        "--background_window",
        type=int,
        default=30,
        help="Number of frames to use for background calculation. Default is 30."
    )
    parser.add_argument(
        "--smooth",
        type=float,
        default=0,
        help="Apply Gaussian smoothing with given sigma. Default is 0 (no smoothing).",
    )
    parser.add_argument(
        "--threshold",
        action="store_true",
        help="Apply thresholding using Yen's method. Default is False."
    )

    args = parser.parse_args()
    process_video(
        args.input_file, args.output_file, args.background_window, args.smooth, args.threshold
    )

if __name__ == "__main__":
    main()
