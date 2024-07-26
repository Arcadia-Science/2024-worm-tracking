import click
import json
import pandas as pd
import os

def read_json(file_path):
    """Read a JSON file and return the data."""
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def extract_data_from_directory(directory):
    """Extract data from all JSON files in the specified directory and its subdirectories."""
    data = {}
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                full_path = os.path.join(root, file)
                # Use full path as the key to avoid name collision
                data[full_path] = read_json(full_path)
    return data

@click.command()
@click.option('--directory', type=click.Path(exists=True), prompt=True, help='Directory containing JSON files.')
@click.option('--output', type=click.Path(), default='output.csv', help='Output CSV file path.')
def main(directory, output):
    """Process JSON files in the specified directory and output to a CSV file."""
    data = extract_data_from_directory(directory)
    if not data:
        click.echo('No JSON files found in the directory.')
        return

    # Convert the dictionary to a DataFrame
    df = pd.DataFrame.from_dict(data, orient='index').transpose()

    # Save to CSV
    df.to_csv(output, index_label='Parameter Name')
    click.echo(f'Data has been written to {output}')

if __name__ == '__main__':
    main()
