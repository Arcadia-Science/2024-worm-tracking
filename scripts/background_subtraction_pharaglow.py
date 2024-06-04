#!/usr/bin/env python

"""background_subtraction.py: Script for background subtraction in worm motility videos."""

import argparse

import imageio.v3 as iio
import numpy as np
import pims
import skimage.io as io
from skimage import filters, morphology, util


@pims.pipeline
def subtract_bg(img, bg):
    """Subtract a background from the image.

    Args:
        img (numpy.array or pims.Frame): input image
        bg (numpy.array or pims.Frame): second image with background

    Returns:
        numpy.array: background subtracted image
    """
    tmp = img - bg
    mi, ma = np.min(tmp), np.max(tmp)
    tmp -= mi
    tmp /= (ma - mi)
    return util.img_as_float(tmp)

@pims.pipeline
def preprocess(img, smooth=0, threshold=None, dilate=False):
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
        img = filters.gaussian(img, smooth, preserve_range=True)
    if threshold is None:
        threshold = filters.threshold_yen(img)
    mask = img >= threshold
    for _ in range(dilate):
        mask = morphology.dilation(mask)
    return mask

def calculate_background(frames, bg_window=30):
    """Calculate the background image using a median stack projection.

    Args:
        frames (numpy.array or pims.ImageSequence): image stack with input images
        bg_window (int): subsample frames for background creation by selecting bg_window numbers of frames evenly spaced. Defaults to 30.

    Returns:
        numpy.array: background image
    """
    select_frames = np.linspace(0, len(frames) - 1, bg_window).astype(int)
    bg = np.median(frames[select_frames], axis=0)
    return bg

def process_video(input_file, output_file, bg_window, smooth, apply_threshold):
    frames = io.imread(input_file)
    bg = calculate_background(frames, bg_window)
    subtracted_frames = [subtract_bg(frame, bg) for frame in frames]

    if smooth:
        subtracted_frames = [filters.gaussian(frame, smooth, preserve_range=True) for frame in subtracted_frames]

    if apply_threshold:
        thresholded_frames = [preprocess(frame, smooth, threshold=filters.threshold_yen(frame)) for frame in subtracted_frames]
        processed_frames = [util.img_as_ubyte(frame) for frame in thresholded_frames]
    else:
        processed_frames = [util.img_as_ubyte(frame) for frame in subtracted_frames]

    fps = iio.immeta(input_file)['fps']
    iio.imwrite(output_file, processed_frames, fps=fps)

def main():
    parser = argparse.ArgumentParser(description="Background subtraction for worm motility videos.")
    parser.add_argument("input_file", type=str, help="Path to the input video file (nd2, tiff, or mov).")
    parser.add_argument("output_file", type=str, help="Path to the output video file.")
    parser.add_argument("--bg_window", type=int, default=30, help="Number of frames to use for background calculation. Default is 30.")
    parser.add_argument("--smooth", type=float, default=0, help="Apply Gaussian smoothing with given sigma. Default is 0 (no smoothing).")
    parser.add_argument("--threshold", action="store_true", help="Apply thresholding using Yen's method. Default is False.")

    args = parser.parse_args()
    process_video(args.input_file, args.output_file, args.bg_window, args.smooth, args.threshold)

if __name__ == "__main__":
    main()
