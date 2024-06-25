import numpy as np
import skimage
from matplotlib import pyplot as plt


def autoscale(im, percentile=100, dtype=None):
    """
    Scale the intensities using percentiles instead of the absolute min and max values.
    """
    if im.dtype == np.bool_:
        im = im.astype(np.float32)

    vmin, vmax = np.percentile(im, [100 - percentile, percentile])
    return skimage.exposure.rescale_intensity(
        im, in_range=(vmin, vmax), out_range=(dtype if dtype is not None else (0, 1))
    )


def imshow(*ims, figsize=(12, 12), title=None):
    """
    Convenience function to visualize one or more images side-by-side.
    """
    plt.figure(figsize=figsize)
    ims = [autoscale(im) for im in ims]
    plt.imshow(np.concatenate(ims, axis=1), cmap="gray")

    if title is not None:
        plt.title(title)
    plt.axis("off")
    plt.show()


def cleanup_mask(mask):
    """
    "Clean" a binary mask by removing small objects and using a closing operation to fill in holes.
    The parameters for these operations were manually selected and are hard-coded for now.
    """
    mask = skimage.morphology.isotropic_closing(mask, radius=5)
    mask = skimage.morphology.remove_small_objects(mask, min_size=100)
    return mask


def tile_image(im, num_timepoints=20, subsample_xy_by=2):
    """
    Tile a single 3D image of shape (timepoints, x, y) into a 2D image of shape (x, timepoints * y).
    """
    # Subsample to reduce the size of the concatenated image.
    subsample_timepoints_by = max(1, im.shape[0] // num_timepoints)
    im_subsampled = im[::subsample_timepoints_by, ::subsample_xy_by, ::subsample_xy_by]

    # Zero-pad the image in the x and y directions to create a black border between the frames
    # after they are concatenated.
    pad_width = 1
    size_t, size_x, size_y = im_subsampled.shape
    im_padded = np.zeros((size_t, size_x + 2 * pad_width, size_y + 2 * pad_width), dtype=im.dtype)
    im_padded[:, pad_width:-pad_width, pad_width:-pad_width] = im_subsampled

    # Concat the timepoints in the x direction (by column).
    size_t, size_x, size_y = im_padded.shape
    im_tiled = im_padded.transpose(1, 0, 2).reshape(size_x, size_t * size_y)

    return im_tiled
