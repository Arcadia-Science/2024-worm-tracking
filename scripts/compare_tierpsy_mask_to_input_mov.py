import argparse

import cv2
import h5py
import numpy as np
from PIL import Image


def load_hdf5_frame(hdf5_file_path, dataset_name, frame_index):
    with h5py.File(hdf5_file_path, "r") as file:
        if dataset_name in file:
            mask_data = file[dataset_name][frame_index]
        else:
            print(f"Dataset {dataset_name} not found in the file.")
            return None
    return mask_data


def load_mov_frame(mov_file_path, frame_index):
    cap = cv2.VideoCapture(mov_file_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()
    if ret:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        print(f"Could not read frame {frame_index} from {mov_file_path}.")
        return None


def compare_frames(hdf5_file_path, mov_file_path, output_file, dataset_name, frame_index):
    hdf5_frame = load_hdf5_frame(hdf5_file_path, dataset_name, frame_index)
    mov_frame = load_mov_frame(mov_file_path, frame_index)

    if hdf5_frame is not None and mov_frame is not None:
        # Normalize the frames to the same range for proper comparison if needed
        hdf5_frame = (hdf5_frame / np.max(hdf5_frame) * 255).astype(np.uint8)
        mov_frame = (mov_frame / np.max(mov_frame) * 255).astype(np.uint8)

        # Create a new image by concatenating both frames side by side
        combined_image = np.hstack((hdf5_frame, mov_frame))

        # Convert the combined image to a PIL Image and save as PNG
        combined_image_pil = Image.fromarray(combined_image)
        combined_image_pil.save(output_file)
    else:
        print("Could not load frames for comparison.")


def main():
    parser = argparse.ArgumentParser(description="Compare frames from an HDF5 file and a MOV file.")
    parser.add_argument("hdf5_file_path", type=str, help="Path to the HDF5 file.")
    parser.add_argument("mov_file_path", type=str, help="Path to the MOV file.")
    parser.add_argument("output_file", type=str, help="Path to save the output PNG file.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="/mask",
        help='Name of the dataset containing the mask in the HDF5 file. Default is "/mask".',
    )
    parser.add_argument(
        "--frame", type=int, default=0, help="Frame index to compare. Default is 0."
    )

    args = parser.parse_args()
    compare_frames(
        args.hdf5_file_path, args.mov_file_path, args.output_file, args.dataset, args.frame
    )


if __name__ == "__main__":
    main()
