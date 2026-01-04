import ormsgpack
import json
from pathlib import Path
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("file", type=Path)
args = parser.parse_args()

path: Path = args.file

with path.open('r') as f:
    data = json.load(f)

packed_data = ormsgpack.packb(data)
with path.with_suffix('.msgpack').open('wb') as f:
    f.write(packed_data)
