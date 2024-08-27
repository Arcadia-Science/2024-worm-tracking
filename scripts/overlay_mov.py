import pathlib

import click
import cv2
import matplotlib.pyplot as plt
import numpy as np


@click.command()
@click.option('--mov-path', type=click.Path(exists=True), required=True, help='Path to the input MOV file.')
@click.option('--output-path', type=click.Path(), required=True, help='Path to save the output PNG image.')

def overlay_mov(mov_path, output_path):
    """
    Overlay all frames in a MOV file and save the resulting image as a PNG.
    """
    mov_file_path = pathlib.Path(mov_path).absolute()

    cap = cv2.VideoCapture(str(mov_file_path))

    if not cap.isOpened():
        raise OSError(f"Cannot open video file {mov_file_path}")

    frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frames.append(gray_frame)

    cap.release()

    frames = np.array(frames)

    # Create min-intensity projection across all frames
    min_proj = np.min(frames, axis=0)

    scaled_image = cv2.normalize(min_proj, None, 0, 255, cv2.NORM_MINMAX)

    output_file_path = pathlib.Path(output_path).absolute()
    plt.imsave(output_file_path, scaled_image, cmap='gray')

    print(f"Overlay image saved as {output_file_path}")

if __name__ == '__main__':
    overlay_mov()
