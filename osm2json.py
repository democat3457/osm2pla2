import numpy as np
import osmium
from pathlib import Path
from argparse import ArgumentParser
import sys
import geopandas as gpd
from shapely.geometry import Point

from lib.coords import Vec2D
from lib.geolib import Projections, CoordsUtil

parser = ArgumentParser()
parser.add_argument("osm_file", type=Path)
args = parser.parse_args()

osm_file: Path = args.osm_file

node_locations = gpd.GeoDataFrame(columns=['location'], geometry='location', crs=Projections.WGS84)

# spawn is at 0.5, 0.5
spawn_id = None
for obj in osmium.FileProcessor(osm_file, osmium.osm.NODE):
    node_locations.loc[obj.id, 'location'] = Point(obj.lon, obj.lat)
    if obj.tags.get("name", "") == "Spawn":
        spawn_id = obj.id

if spawn_id is None:
    print("ERROR: did not find a Spawn node!")
    sys.exit(1)

node_locations = CoordsUtil._to_projected_crs(node_locations)

# central park has corners at (-111,-111), (112, 112)
central_park_corners = None
for obj in osmium.FileProcessor(osm_file, osmium.osm.WAY):
    if obj.tags.get("name", "") == "Central Park" and obj.is_closed():
        central_park_corners = node_locations.loc[[n.ref for n in obj.nodes][:-1]]
        break

if central_park_corners is None:
    print("ERROR: could not find reference points (central park)")
    sys.exit(1)

spawn_offset_pt = node_locations.at[spawn_id, 'location']
spawn_offset = Vec2D(spawn_offset_pt.x, spawn_offset_pt.y)

cp_corners_pt = central_park_corners["location"]
cp_corners = [ Vec2D(c.x, c.y) for c in cp_corners_pt ]

print("Spawn offset:", spawn_offset)
print("Park corners:", cp_corners)

# assume park is square and centered on spawn, find scale
scale = 111.5 / np.mean(np.mean([abs(c - spawn_offset) for c in cp_corners]).tup)
def transform_utm_to_mc(x):
    vectorized = Vec2D.from_(x['location'])
    with_offset = vectorized - spawn_offset
    scaled = with_offset * scale
    with_spawn_offset = scaled + (0.5, 0.5) # spawn is at 0.5,0.5
    return with_spawn_offset
node_mc_coords = node_locations.apply(transform_utm_to_mc, axis=1)
print(node_mc_coords)
