import json
import csv
import sys, os
import math

symetries_2P = [
	"N-S", "E-W", # straight 2P
	"180", # central 2P
	"NW-SE", "SW-NE", # diagonal 2P
]
symetries_4P = [
	"cross-straight-NvS", # straight 4P North VS South
	"cross-straight-EvW", # straight 4P East VS West
	"cross-straight-90", # straight 4P FFA
	"cross-diag-NWvSE", # diagonal 4P North-West VS South-East
	"cross-diag-NEvSW", # diagonal 4P North-East VS South-West
	"cross-diag-90", #diagonal 4P FFA
]

def tile_to_coord(tile):
	return round(tile * 128) + 64

def deg_to_rotation(deg):
	return round(deg / 360.0 * 65536) % 65536

def symetryze(obj, width, height, symetry, forPlayer):
	width = width - 1
	height = height - 1
	newId = "%d%s"%(forPlayer, obj["id"][1:])
	offset = 0
	if obj["size"] == 2:
		offset = 1
	if symetry == "N-S" or symetry == "S-N" \
	or (symetry == "cross-straight-EvW" and (forPlayer == 1 or forPlayer == 3)) \
	or (symetry == "cross-straight-NvS" and forPlayer == 2) :
		return {
			"name": obj["name"],
			"id": newId,
			"x": obj["x"],
			"y": height - obj["y"],
			"rot": (180 - obj["rot"]) % 360,
			"owner": forPlayer,
			"size": obj["size"]
		}
	elif symetry == "E-W" or symetry == "W-E" \
	or (symetry == "cross-straight-NvS" and (forPlayer == 1 or forPlayer == 3)) \
	or (symetry == "cross-straight-NvS" and forPlayer == 2) :
		return {
			"name": obj["name"],
			"id": newId,
			"x": width - obj["x"] + offset,
			"y": obj["y"],
			"rot": (360 - obj["rot"]) % 360,
			"owner": forPlayer,
			"size": obj["size"]
		}
	elif symetry == "180":
		return {
			"name": obj["name"],
			"id": newId,
			"x": width - obj["x"] + offset,
			"y": height - obj["y"] + offset,
			"rot": (180 + obj["rot"]) % 360,
			"owner": forPlayer,
			"size": obj["size"]
		}
	elif symetry == "NW-SE" \
	or (symetry == "cross-diag-NWvSE" and forPlayer == 2) \
	or (symetry == "cross-diag-NEvSW" and (forPlayer == 1 or forPlayer == 3)):
		axis = ((math.atan(height / width) * 180 / math.pi) + 90) % 360
		return {
			"name": obj["name"],
			"id": newId,
			"x": (height - obj["y"]) / height * width + offset,
			"y": (width - obj["x"]) / width * height + offset,
			"rot": (axis - (obj["rot"] - axis)) % 360,
			"owner": forPlayer,
			"size": obj["size"]
		}
	elif symetry == "SW-NE" \
	or (symetry == "cross-diag-NEvSW" and forPlayer == 2) \
	or (symetry == "cross-diag-NWvSE" and (forPlayer == 1 or forPlayer == 3)):
		axis = ((math.atan(-height / width) * 180 / math.pi) + 90) % 360
		return {
			"name": obj["name"],
			"id": newId,
			"x": obj["y"] / height * width,
			"y": obj["x"] / width * height,
			"rot": (axis - (obj["rot"] - axis)) % 360,
			"owner": forPlayer,
			"size": obj["size"]
		}
	# case end
	print ("Unsupported symetry %s for player %d"%(symetry, forPlayer))
	return None
# symetryze end

def csvline_to_object(row):
	size = 1
	if len(row) >= 7 and row[6]:
		size = int(row[6])
	return {
		"id": row[0],
		"name": row[1],
		"x": float(row[2]),
		"y": float(row[3]),
		"rot": int(row[4]),
		"owner": int(row[5]),
		"size": size
	}

def jsonify_droids(droids):
	json = {}
	for d in droids:
		json[d["id"]] = {
			"position": [tile_to_coord(d["x"]), tile_to_coord(d["y"])],
			"rotation": [deg_to_rotation(d["rot"]), 0, 0],
			"startpos": int(d["owner"]),
			"template": d["name"]
		}
	return json

def jsonify_structs(structs):
	json = {}
	for s in structs:
		json[s["id"]] = {
			"position": [tile_to_coord(s["x"]) - 64, tile_to_coord(s["y"]) - 64],
			"rotation": [deg_to_rotation(s["rot"]), 0, 0],
			"startpos": int(s["owner"]),
			"name": s["name"]
		}
	return json

def jsonify_features(feats):
	json = {}
	for f in feats:
		json[f["id"]] = {
			"position": [tile_to_coord(f["x"]), tile_to_coord(f["y"])],
			"rotation": [deg_to_rotation(f["rot"]), 0, 0],
			"name": f["name"]
		}
	return json

def read_map_props(filepath):
	with open(filepath, 'r') as props_file:
		props = json.load(props_file)
	#open end
	return props

if len(sys.argv) < 2:
	print("Usage:")
	print("	wzobjectcompiler.py mapdir")
	exit()

mapdir = sys.argv[1]

if mapdir == '.':
	mapdir = os.getcwd()

try:
	props = read_map_props(os.path.join(mapdir, "map.json"))
except FileNotFoundError:
	print("Cannot read %s"%os.path.join(mapdir, "map.json"))
	exit()
except json.decoder.JSONDecodeError as e:
	print("Cannot parse %s: %s"%(os.path.join(mapdir, "map.json"), e))
	exit()
width = props['width']
height = props['height']

symetry = None

if "symetry" in props:
	all_symetries = []
	all_symetries.extend(symetries_2P)
	all_symetries.extend(symetries_4P)
	if not props["symetry"] in all_symetries:
		print("Unknown symetry %s, must be one of %s"%(props['symetry'], all_symetries))
		exit()
	symetry = props['symetry']

files = ["droid", "struct", "feature"]
# droids

for f in files:
	with open(os.path.join(mapdir, "%s.csv"%(f)), newline='') as csvfile:
		data = csv.reader(csvfile, delimiter=',', quotechar='"')
		i = 0
		objs = []
		for row in data:
			i = i+1
			if i == 1:
				continue # skip header
			obj =  csvline_to_object(row)
			objs.append(obj)
			if obj["id"][0:3] == "0P-":
				if symetry in symetries_2P:
					objs.append(symetryze(obj, width, height, symetry, 1))
				elif symetry in symetries_4P:
					objs.append(symetryze(obj, width, height, symetry, 1))
					obj2 = symetryze(obj, width, height, symetry, 2)
					objs.append(obj2)
					objs.append(symetryze(obj2, width, height, symetry, 3))
				# if symetry end
			#if obj.name end
		# for row end
		jsonObjs = None
		if (f == "droid"):
			jsonObjs = jsonify_droids(objs)
		elif (f == "struct"):
			jsonObjs = jsonify_structs(objs)
		elif (f == "feature"):
			jsonObjs = jsonify_features(objs)
		with open(os.path.join(mapdir, "%s.json"%f), 'w', encoding="utf-8") as output:
			output.write(json.dumps(jsonObjs, ensure_ascii=False, indent=4))
		# with open json end
	# with open csv end
# for end
