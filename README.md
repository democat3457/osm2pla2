# JOSM format to PLA2 converter

Using JOSM to edit maps for the custom file type, PLA2, used in Minecart Rapid Transit (MRT) server mapping.

## JOSM Preparation

1. Open JOSM, but do not download any data.
2. Go to JOSM settings, go to Map and select the UTM projection. Any zone will do, I've chosen zone 15.
3. In the Plugins tab on the settings, download the PicLayer plugin to be able to import Dynmap pictures of the city.
4. Import photos of your city into the area of JOSM that is the most unwarped.
5. Scale the city photos down such that they are approximately scaled to between 0.8 and 2 meters per block of Dynmap. <insert guide>
6. Map your city like you would a normal map.
7. Save the changes as a .osm file. Optionally, save the JOSM session so you can save the settings and photo position.

## PLA2 Conversion

1. Run the `osm2json.py` script with the file path of the .osm file to produce a .pla2.json file.
2. Run `scripts/pack.py` to pack the pla2 into a msgpack for storage and upload.
