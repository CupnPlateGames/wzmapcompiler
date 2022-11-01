Warzone 2100 map compiler
=========================

A simple compiler to create binaries and .wz files for map from various png maps. This is a quick and dirty proof of concept for a map compiler that doesn't require any rendering nor GUI, but still a functional one. It aims to be able to build maps with the least amount of dedicated tools, using almost exclusively your favorite external image processing software.

Licenced under GPL v2 or any later.

What is does
------------
Reading heightmap, tilemap, cliffmap and compiling them into a `.map` file. It also include it into a `.wz` file as well as other required and generated files like the `.addon.lev` and `.gam`. External json files are also included for conveniency to generate a playable map file. A tool is provided to compile some csv files into those json files with symetry.

What it does not
----------------

Pre-rendering maps, creating a preview image. You'll have to use your imagination and check what it actually looks like directly from the game.

Checking actual data. The compiler doesn't require any game data, non-existant objects will throw errors only when running the game.

What is missing
---------------
- Cliff texture orientation (and generally texture orientation)
- Only supports rockies and Arizona tileset with a `ttypes.ttp` file that was copied from an existing map
- Reads only 8-bits pixel maps, it doesn't use the new json format that could handle 16-bits values
- Generating output png files for textures errors (unknown color from tilemap or cliff that doesn't have a cliff texture associated to the terrain type)

Prerequisites
=============

Python3 with PIL, or pillow

Install it with something like
```
sudo apt install python3-pil
```

Why Python? Because it's a proof of concept. The "best" language would be C++ to be able to use some of the game code in the future. Like using the existing 3D renderer as a preview or existing map format-related functions. What is interesting is the experimental map making process, not the current code.

Creating the json files
=======================

The optional `wzobjectcompiler` script reads objects from csv files and create the corresponding json files. It reads `droid.csv`, `struct.csv` and `feature.csv` to create `droid.json`, `struct.json` and `feature.json`, that are then used by the map compiler to create the complete map.

The csv files contains a header and the following columns in that order:

- `Id`: the identifier of the object. It can be anything. When the id starts with `0P-`, multiple objects will be created according to the symetry of the map. Even for features that are not technically owned by a player.
- `Name`: the template or object name, as defined in game data.
- `X`: the horizontal coordinate in tile of the object. A round number correspond to the middle of the tile.
- `Y`: the vertical coordinate in tile of the object. A round number correspond to the middle of the tile.
- `Rotation`: rotation in degrees.
- `Owner`: the player number, starting from 0. Feature has an owner to indicate in which player area it is.
- `Size` (only for struct.csv): the size of the structure in tiles. It is used to compute the right coordinate when creating other symetrical structures.

Then you can run the script.

```
python3 ../wzobjectcompiler.py <map directory>
```

See below to add symetry with the `map.json` file that is used by the map compiler as well.

Running the compiler
====================

Create a directory named after your map in the compiler directory (or anywhere if you know how to install python scripts properly). Copy `rockies.ttp` inside and rename it `ttypes.ttp` and create a `map.json` file (see below). Create a `heightmap.png`, `cliffmap.png` and `tilemap.png` in that folder (see below). Add your `droid.json`, `feature.json` and `struct.json`.

A map directory ready for compilation must contains the following files:

- cliffmap.png
- droid.json
- feature.json
- gatemap.png (optional)
- heightmap.png
- map.json
- struct.json
- tilemap.png
- ttypes.ttp (which is a copy of the rockies.ttp file from the compiler)

A small sample map is provided with the source code.

When ready, run from that map directory:

```
python3 ../wzmapcompiler.py <map directory>
```
with the number of tiles of your map. It should be the same size as your png maps minus one (that is a map of 64x64 tiles uses maps of 65x65 pixels).

The map files are looked inside the current working directory, and the directory name will be the name of the map.

When everything goes well, a .wz file is generated containing your map, you can copy this file to your Warzone2100 map directory and play it.

Autogenerating cliffmap
-----------------------
When a heightmap is available, run

```
python3 ../wzmapcompiler.py autocliff <map directory>
```

to automatically generate a cliffmap. It will be created in autocliffmap.png, you can directly move it to cliffmap.png or merge it into your existing cliffmap.

You can also provide the minimum height difference in pixel value as a parameter after autocliff.

Creating the map.json file
==========================

The map definition contains some informations about the map to compile. It is a json file with the following properties:

- `width`: the width of the map in tiles
- `height`: the height of the map in tiles
- `players`: the number of players on the map
- `env`: the environment to use, either `rockies` or `arizona` (urban not supported yet)
- `name`: (optional) an alternative map name. When not provided, the map directory is used as its name.
- `symetry`: (optional) define which symetry to use when creating objects with `wzobjectcompiler`.

The `name` has some restrictions, that applies either to the `name` property or the directory name when not set. For example the game may not be able to read the map file if the name starts with a number.

For readability in the game, names should not be too long. 16 characters or more should be avoided, but that doesn't prevent the map to be listed.

When no symetry is provided, objects are not duplicated. The available symetries are as follow:

- `N-S`: North to South (Y coordinate are inverted).
- `E-W`: East to West (X coordinates are inverted).
- `180`: Central symetry.
- `NW-SE`: North-West to South-East (top-left becomes bottom-right).
- `SW-NE`: South-West to North-East (bottom-left becomes top-right).
- `cross-straight-NvS`: mostly for 2v2 maps, North VS South, with East and West objects being symetrical, then duplicated for the other team.
- `cross-straight-EvW`: mostly for 2v2 maps, East VS Weast, with North and South objects being symetrical, then duplicated for the other team.
- `cross-straight-90`: mostly for 4 free-for-all maps, each corner being rotated by 90° around the center.
- `cross-diag-NWvSE`: mostly for 2v2 maps, North-West VS South-East, with North being duplicated to West, then duplicated for the opposite corner.
- `cross-diag-NEvSW`:  mostly for 2v2 maps, North-Eeast VS South-West, with North being duplicated to East, then duplicated for the opposite corner.
- `cross-diag-90`: mostly for 4 free-for-all maps, each side being rotated by 90° around the center.

Only objects which id start with `0P-` are duplicated. All other objects are not affected by the symetry.

Painting the map files
======================

The heightmap
-------------
The heightmap defines the altitude of each vertice. A vertice is a corner of a tile, so the heightmap is the size of the map + 1 pixel wide and tall.

The heightmap is a grayscaled picture. Each pixel defines the heigh of the corresponding vertice, with black being altitude 0 (bottom) and pure white the maximum altitude.

The compiler can handle RGB values. When using RGB files, the red channel is read for the value (painting from black to pure red has the same effect as painting black to pure white).


The cliffmap
------------
This map can be autogenerated when the heightmap is done. When it is not fine enough, you can still edit this map by hand.

The cliffmap defines which tiles are an unpassable cliff. Each pixels represents a tile (and not a vertice), so the size of the cliffmap is exactly the size of the map. For conveniency to be able to superpose the cliffmap to the heightmap, it can be of the same size, but the extra pixel to the right and the bottom is just ignored.

An important slope is remarkable in the heightmap when two adjacent pixels are contrasting.

A tile is considered a cliff when the pixel is not black (transparency is allowed). When painting cliffs, mark the top-left vertice of the tile. As each tile is composed of 4 vertices, you can mark a cliff when the pixel to the right or just below or below on the right is of significant different height.

Note that when 2 cliff pixels touch diagonally, the terrain won't be passable between them.

A pixel is considered to be a cliff if:

- it is not very transparent for files with alpha channel (more than 16 of 255 in alpha value)
- it is not too black in RGB (the sum of 3 colors is more than 16)
- it is not too black in greyscale (value above 16)


The tilemap
-----------
The tilemap defines the terrain. Each pixel represents a vertice and can be colored with the given values :

For rockies environment:

- Grass: #2c3b27
- Gravel: #6c6662
- Dirt: #5a5040
- Snowy grass: #8e908a
- Snowy gravel: #9e9a97
- Snow: #f1f1f1
- Concrete: #636565
- Water: #1d2f4d

For Arizona environment:

- Red: #ff0000
- Yellow: #808000
- Sand: #ffff00
- Brown: #404040
- Green: #008000
- Concrete #000000
- Water: #0000ff

Any pixel outside those values will raise an error about unknown tiles and it will be rendered as grass (tile 0)

Note that the game renderer will try to generate transitions between terrain types smoothly, so the actual rendering may be different when multiple terrain types are present close one to an other.

The right-most and bottom-most pixel lines are only used to subtilely start a transition outside the map.


The gatemap
-----------
This map defines locations where the AI should place defense buildings. When no gatemap is provided, the map is compiled without gateways.

Like the cliffmap, the gatemap uses colored pixels to define gateways. A gate is a line of colored pixels, the AI will place gate defenses around them.


Tips
====

Naming convention
-----------------
To be able to sort maps from your directories, the compiler adds `Xc-` with X the number of players to the wz file name. It has no effect in game. If your map is named `MyCompiledMap` for 2 players, it will create `2c-MyCompiledMap.wz`.

Unbuildable sides of the map
----------------------------
The first tile around the map is not buildable nor passable. The second tile may be passable but is never buildable. To avoid making some gateway not closeable, the two tiles around the map should not be passable anyway.

Symetry
-------
Because the maps represents vertices and not tiles, symetric maps should have 1px in common from both sides. For example a vertical symetry of a map of 64 tiles (65 pixels) should have either each sides 33 pixels wides, with the 33rd pixels in common for both sides, or each sides of 32 pixels with a central line of pixels not overlapping any sides.