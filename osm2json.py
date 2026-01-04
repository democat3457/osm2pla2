import numpy as np
import osmium
from pathlib import Path
from argparse import ArgumentParser
import sys
import geopandas as gpd
from shapely.geometry import Point

from lib.coords import Vec2D
from lib.geolib import Projections, CoordsUtil
from lib.pla2 import Pla2Object, Pla2ObjectCollection

parser = ArgumentParser()
parser.add_argument("osm_file", type=Path)
args = parser.parse_args()

osm_file: Path = args.osm_file

node_locations = gpd.GeoDataFrame(columns=['location'], geometry='location', crs=Projections.WGS84)

# spawn is at 0.5, 0.5
spawn_id = None
for o in osmium.FileProcessor(osm_file, osmium.osm.NODE):
    node_locations.loc[o.id, 'location'] = Point(o.lon, o.lat)
    if o.tags.get("name", "") == "Spawn":
        spawn_id = o.id

if spawn_id is None:
    print("ERROR: did not find a Spawn node!")
    sys.exit(1)

node_locations = CoordsUtil._to_projected_crs(node_locations)

# central park has corners at (-111,-111), (112, 112)
central_park_corners = None
for o in osmium.FileProcessor(osm_file, osmium.osm.WAY):
    if o.tags.get("name", "") == "Central Park" and o.is_closed():
        central_park_corners = node_locations.loc[[n.ref for n in o.nodes][:-1]]
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
scale: float = 111.5 / np.mean(np.mean([abs(c - spawn_offset) for c in cp_corners]).tup)
def transform_utm_to_mc(x):
    vectorized = Vec2D.from_(x['location'])
    with_offset = vectorized - spawn_offset
    scaled = with_offset * scale
    scaled.y *= -1 # mc coords have southeast as positive, while utm has northeast as positive
    with_spawn_offset = scaled + (0.5, 0.5) # spawn is at 0.5,0.5
    return with_spawn_offset
node_mc_coords = node_locations.apply(transform_utm_to_mc, axis=1)
# print(node_mc_coords)


# Convert geometry to PLA2


def check_all_tags(o, *tags: tuple[str, str]):
    return all((o.tags.get(k, "<unset>") != "<unset>") if v == "*"
               else (o.tags.get(k, "<unset>") == v) for k,v in tags)

def check_any_tags(o, *tags: tuple[str, str]):
    return any((o.tags.get(k, "<unset>") != "<unset>") if v == "*"
               else (o.tags.get(k, "<unset>") == v) for k,v in tags)


pla2objs = Pla2ObjectCollection("ccy")

for o in osmium.FileProcessor(osm_file, osmium.osm.NODE | osmium.osm.WAY)\
                 .with_filter(osmium.filter.EmptyTagFilter()):
    # common tags
    name = o.tags.get("name", "")
    alt_name = o.tags.get("alt_name", "") # currently unused, no field exists in pla2
    layer = float(o.tags.get("layer", "0"))

    if isinstance(o, osmium.osm.Node):
        location: Vec2D = node_mc_coords.loc[o.id]
        if check_all_tags(o, ("tourism", "attraction")):
            pla2objs.add(Pla2Object(type="attraction",
                                    nodes=[location],
                                    display_name=name,
                                    layer=layer))
        elif check_any_tags(o, ("amenity", "fast_food"), ("amenity", "restaurant"), ("amenity", "cafe")):
            pla2objs.add(Pla2Object(type="restaurant",
                                    nodes=[location],
                                    display_name=name,
                                    layer=layer))
        elif check_all_tags(o, ("parking", "*")):
            pla2objs.add(Pla2Object(type="parking",
                                    nodes=[location],
                                    display_name=name,
                                    layer=layer))
    elif isinstance(o, osmium.osm.Way):
        node_ids = [n.ref for n in o.nodes]
        if o.is_closed():   # pla2 removes end nodes for areas and depends on type to determine areas
            node_ids = node_ids[:-1]
        nodes: list[Vec2D] = node_mc_coords.loc[node_ids].tolist()
        if check_all_tags(o, ("highway", "*")):
            pedestrian = check_any_tags(o, ("vehicle", "no"), ("access", "no")) and check_any_tags(o, ("foot", "yes"), ("foot", "designated"))
            HIGHWAY_LEVELS = {
                "trunk": 0,
                "primary": 1,
                "secondary": 2,
                "tertiary": 3,
                "residential": 4,
                "service": 5,
            }
            highway_level = HIGHWAY_LEVELS.get(o.tags.get("highway"), 5)
            hwy_level_offset = -1
            highway_level = max(0, min(4, highway_level + hwy_level_offset))
            PLA2_HIGHWAYS = {
                0: "localHighway",
                1: "localMainRoad",
                2: "localSecondaryRoad",
                3: "localTertiaryRoad",
                4: "localQuaternaryRoad"
            }
            type = PLA2_HIGHWAYS[highway_level]
            if o.tags.get("highway") == "pedestrian":
                type = "localPedestrianTertiaryRoad"
            elif highway_level <= 3 and pedestrian:
                type = "localPedestrianTertiaryRoad"
            elif highway_level >= 4 and pedestrian:
                type = "localPedestrianQuaternaryRoad"

            oneway = check_any_tags(o, ("oneway", "yes"), ("oneway", "-1"))
            if oneway and o.tags["oneway"] == "-1":
                nodes = list(reversed(nodes)) # -1 means the street is oneway, but going the other direction - to produce in pla2, reverse the way direction
            tags = ["oneWay"] if oneway else []
            
            elevated = check_all_tags(o, ("bridge", "yes"))
            if elevated:
                layer -= 1 # because pla2 renders elevated streets over non-elevated streets automatically, no need to put on different rendering layer
            underground = check_all_tags(o, ("tunnel", "yes"))
            if underground:
                layer += 1 # because pla2 renders underground streets under non-underground streets automatically, no need to put on different rendering layer

            if elevated and underground:
                print(f"WARN: Way {o.id} is both elevated and underground!")
                elevated = False
                underground = False
            
            if elevated:
                type += "_elevated"
            if underground:
                type += "_underground"

            pla2objs.add(Pla2Object(type=type, nodes=nodes, display_name=name, layer=layer, tags=tags))
        elif check_all_tags(o, ("leisure", "park")):
            pla2objs.add(Pla2Object(type="park",
                                    nodes=nodes,
                                    display_name=name,
                                    layer=layer))
        else:
            print(o)

with osm_file.with_suffix(".pla2.json").open("w") as fp:
    pla2objs.to_json(fp)
