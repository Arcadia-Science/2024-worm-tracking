import cv2
import numpy as np


def getROIMask(
    image,
    min_area,
    max_area,
    thresh_block_size,
    thresh_C,
    dilation_size,
    keep_border_data,
    is_light_background,
    wells_mask=None,
):
    """
    Calculate a binary mask to mark areas where it is possible to find worms.
    Objects with less than min_area or more than max_area pixels are rejected.
        > min_area -- minimum blob area to be considered in the mask
        > max_area -- max blob area to be considered in the mask
        > thresh_C -- threshold used by openCV adaptiveThreshold
        > thresh_block_size -- block size used by openCV adaptiveThreshold
        > dilation_size -- size of the structure element to dilate the mask
        > keep_border_data -- (bool) if false it will reject any blob that touches the image border
        > is_light_background -- (bool) true if bright field, false if fluorescence
        > wells_mask -- (bool 2D) mask that covers (with False) the edges of wells in a MW plate
    """
    # Objects that touch the limit of the image are removed. I use -2 because
    # openCV findCountours remove the border pixels
    IM_LIMX = image.shape[0] - 2
    IM_LIMY = image.shape[1] - 2

    # this value must be at least 3 in order to work with the blocks
    thresh_block_size = max(3, thresh_block_size)
    if thresh_block_size % 2 == 0:
        thresh_block_size += 1  # this value must be odd

    # let's add a median filter, this will smooth the image,
    # and eliminate small variations in intensity
    # now done with opencv instead of scipy
    image = cv2.medianBlur(image, 5)

    # adaptative threshold is the best way to find possible worms. The
    # parameters are set manually, they seem to work fine if there is no
    # condensation in the sample
    # invert the threshold (change thresh_C->-thresh_C and cv2.THRESH_BINARY_INV->cv2.THRESH_BINARY)
    # if we are dealing with a fluorescence image
    if not is_light_background:
        mask = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, thresh_block_size, -thresh_C
        )
    else:
        mask = cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV,
            thresh_block_size,
            thresh_C,
        )

    # find the contour of the connected objects (much faster than labeled
    # images)

    contours, hierarchy = cv2.findContours(mask.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[-2:]

    # find good contours: between max_area and min_area, and do not touch the
    # image border
    goodIndex = []
    for ii, contour in enumerate(contours):
        if not keep_border_data:
            if wells_mask is None:
                # eliminate blobs that touch a border
                # TODO: double check this next line. I suspect contour is in
                # x,y and not row columns
                keep = (
                    not np.any(contour == 1)
                    and not np.any(contour[:, :, 0] == IM_LIMY)
                    and not np.any(contour[:, :, 1] == IM_LIMX)
                )
            else:
                # keep if no pixel of contour is in the 0 part of the mask
                keep = not np.any(wells_mask[contour[:, :, 1], contour[:, :, 0]] == 0)
        else:
            keep = True

        if keep:
            area = cv2.contourArea(contour)
            if (area >= min_area) and (area <= max_area):
                goodIndex.append(ii)

    # typically there are more bad contours therefore it is cheaper to draw
    # only the valid contours
    mask = np.zeros(image.shape, dtype=image.dtype)
    for ii in goodIndex:
        cv2.drawContours(mask, contours, ii, 1, cv2.FILLED)

    # drawContours left an extra line if the blob touches the border. It is
    # necessary to remove it
    mask[0, :] = 0
    mask[:, 0] = 0
    mask[-1, :] = 0
    mask[:, -1] = 0

    # dilate the elements to increase the ROI, in case we are missing
    # something important
    struct_element = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilation_size, dilation_size))
    mask = cv2.dilate(mask, struct_element, iterations=3)

    return mask
