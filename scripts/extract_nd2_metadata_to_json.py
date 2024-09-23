import json
from pathlib import Path

import click
import nd2


def serialize_metadata(data):
    """
    Convert complex metadata objects to a serializable format.
    Handles dictionaries, lists, and basic data types by converting non-serializable types to
        strings.
    """
    if isinstance(data, dict):
        return {key: serialize_metadata(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_metadata(item) for item in data]
    elif isinstance(data, str | int | float | bool | type(None)):
        return data
    else:
        return str(data)


@click.option("--nd2-path", type=Path, help="Path to the nd2 file")
@click.option("--json-path", type=Path, help="Path to output json file")
@click.command()
def main(nd2_path: str, json_path: str) -> None:
    """
    Reads an ND2 file and writes its metadata to a JSON file.

    Args:
        nd2_path (str): Path to the ND2 file.
        json_path (str): Path to the output JSON file.

    Returns:
        None
    """
    with nd2.ND2File(nd2_path) as nd2_file:
        metadata = nd2_file.metadata

    serializable_metadata = serialize_metadata(metadata)

    with open(json_path, "w") as json_file:
        json.dump(serializable_metadata, json_file, indent=4)

    print(f"Metadata from {nd2_path} has been written to {json_path}")


if __name__ == "__main__":
    main()
