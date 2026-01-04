import ormsgpack
import json
from pathlib import Path
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("file", type=Path)
args = parser.parse_args()

path: Path = args.file

with path.open('rb') as f:
    data = f.read()

unpacked_data = ormsgpack.unpackb(data)
with path.with_suffix('.json').open('w') as f:
    json.dump(unpacked_data, f, indent=2)
