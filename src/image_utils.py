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


def cleanup_mask(mask, closing_radius=5, min_region_size=100):
    """
    "Clean" a binary mask by removing small objects and using a closing operation to fill in holes.
    """
    mask = skimage.morphology.isotropic_closing(mask, radius=closing_radius)
    mask = skimage.morphology.remove_small_objects(mask, min_size=min_region_size)
    return mask


def tile_images_2d(ims, num_rows=5, subsample_xy_by=2):
    """
    Tile a 3D image of shape (n, xy_size, xy_size) into a single 2D image of tiled images.
    """
    ims = ims[:, ::subsample_xy_by, ::subsample_xy_by]

    num_cols = np.ceil(len(ims) / num_rows).astype(int)

    # Pad the x and y dimensions with zeros so that each image has a black border.
    pad_width = 1
    size_n, size_x, size_y = ims.shape
    ims_padded = np.zeros((size_n, size_x + 2 * pad_width, size_y + 2 * pad_width), dtype=ims.dtype)
    ims_padded[:, pad_width:-pad_width, pad_width:-pad_width] = ims

    # Create a new array padded with zeros so that it is a multiple of n.
    xy_size = ims_padded.shape[1]
    tiled_image = np.zeros((num_rows * num_cols, xy_size, xy_size), dtype=ims.dtype)
    tiled_image[: len(ims_padded)] = ims_padded

    # Reshape the padded image into a 2D grid of individual images.
    tiled_image = (
        tiled_image.reshape(num_rows, num_cols, xy_size, xy_size)
        .transpose(0, 2, 1, 3)
        .reshape(num_rows * xy_size, num_cols * xy_size)
    )
    return tiled_image


def tile_images_1d(im, num_timepoints=20, subsample_xy_by=2):
    """
    Tile a 3D image of shape (num_timepoints, xy_size, xy_size) into a 2D image
    of concatenated timepoints of shape (xy_size, num_timepoints * xy_size).
    """
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
