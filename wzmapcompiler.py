from PIL import Image
import zipfile
import json
import os, sys, shutil

# RGB codes to tile index
rockies_tiledef = {
	# Rocky as set in FlaME
	(44,59,39): 0, # grass
	(108,102,98): 5, # gravel
	(90,80,64): 53, # dirt
	(142,144,138): 23, # grass snow
	(158,154,151): 41, # gravel snow
	(241,241,241): 64, # snow
	(99,101,101): 22, # concrete
	(29,47,77): 17 # water
}
arizona_tiledef = {
	# Arizona as set in FlaME
	(255,0,0): 48, # red
	(128,128,0): 9, # yellow
	(255,255,0): 12, # sand
	(64,64,64): 5, # brown
	(0,128,0): 23, # green
	(0,0,0): 22, # concrete
	(0,0,255): 17, # water
}
# Regular tile index to cliff tile index 
rockies_cliffdef = {
	# Rocky cliffs
	5: 46, # gravel to gravel cliff
	41: 44, # gravel snow to gravel snow cliff
	23: 29, # grass snow to grass snow cliff
	64: 76, # snow to snow cliff
	"default": 46
}
arizona_cliffdef = {
	# Arizona cliffs
	48: 71, # red to red cliff
	"default": 71
}
default_autocliff_diff = 50 # roughly 35°
env_tiledef = {
	"r": rockies_tiledef,
	"a": arizona_tiledef,
}
env_cliffdef = {
	"r": rockies_cliffdef,
	"a": arizona_cliffdef,
}
env_dataset = {
	"r": "MULTI_CAM_3",
	"a": "MULTI_CAM_1",
}

def num_to_32bits(num):
	"""Convert a int32 to a 4-bytes array"""
	b0 = int((num&0xff000000)/0x01000000)	
	b1 = int((num&0x00ff0000)/0x00010000)
	b2 = int((num&0x0000ff00)/0x00000100)
	b3 = int(num&0x000000ff)
	return bytearray([b3,b2,b1,b0])

def heightmap_to_bytes(filename):
	"""Read heightmap in filename and return the height byte array"""
	try:
		img = Image.open(filename)
	except FileNotFoundError:
		print("File %s not found"%filename)
		return
	except Error:
		print("Error reading %s"%filename)
		return
	mode = img.mode
	width,height = img.size
	bytes = []
	print("Reading heightmap %s as %s" % (filename, mode))
	if mode != "RGB" and mode != "RGBA" and mode != "L":
		print("Cannot parse heightmap, accepting only RGB, RGBA or L (greyscale)")
		return
	for y in range(height-1):
		for x in range(width-1):
			px = img.getpixel((x, y))
			# px is a tuple of values for each channels
			bytes.append(px[0])
		#end-for
	#end-for
	return bytes


def px_to_tile(px, tiledef):
	"""Get the tile index from a pixel color"""
	rgb = (px[0], px[1], px[2])
	if not rgb in tiledef:
		return
	return tiledef[rgb]

def tile_to_cliff(t, cliffdef):
	"""Get the cliff tile index from a tile index"""
	if not t in cliffdef:
		return
	return cliffdef[t]

def px_as_boolean(px, mode):
	if mode == "RGBA":
		return px[3] > 16 # alpha detection
	elif mode == "RGB":
		return px[0] + px[1] + px[2] > 16 # not black
	else:
		return px[0] > 16 # not black either

def tilemap_to_bytes(tilefilename, clifffilename, env):
	"""Get an array of tile indexes from the tilemap stored in tilefilename mixed with clifffilename"""
	try:
		timg = Image.open(tilefilename)
	except FileNotFoundError:
		print("File %s not found"%tilefilename)
		return
	except Error:
		print("Error reading %s"%tilefilename)
		return
	try:
		cimg = Image.open(clifffilename)
	except FileNotFoundError:
		print("File %s not found"%clifffilename)
		return
	except Error:
		print("Error reading %s"%clifffilename)
		return
	tmode = timg.mode
	cmode = cimg.mode
	width,height = timg.size
	if width != cimg.size[0] or height != cimg.size[1]:
		print("Tile map and cliff map are not the same size")
		return
	bytes = []
	terror = False
	cerror = False
	print("Reading tilemap %s as %s" % (tilefilename, tmode))
	print("Reading cliffmap %s as %s" % (clifffilename, cmode))
	if tmode != "RGB" and tmode != "RGBA" and tmode != "L":
		print("Cannot parse tilemap, accepting only RGB, RGBA or L (greyscale)")
		return
	if cmode != "RGB" and cmode != "RGBA" and cmode != "L":
		print("Cannot parse cliffmap, accepting only RGB, RGBA or L (greyscale)")
		return
	tiledef = env_tiledef[env[0]]
	cliffdef = env_cliffdef[env[0]]
	for y in range(height-1):
		for x in range(width-1):
			px = timg.getpixel((x, y))
			tile = px_to_tile(px, tiledef)
			cpx = cimg.getpixel((x,y))
			iscliff = px_as_boolean(cpx, cmode)
			if not tile:
				if iscliff:
					bytes.append(cliffdef['default'])
				else:
					bytes.append(0)
				terror = True
			else:
				if iscliff:
					tile = tile_to_cliff(tile, cliffdef)
				if not tile:
					bytes.append(cliffdef['default'])
					cerror = True
				else:
					bytes.append(tile)
				#if-else-end
			#if-else-end
		#end-for
	#end-for
	if terror:
		print("Error(s) while reading tilemap: unknown tile(s)")
	if cerror:
		print("Error(s) while reading cliffmap: incompatible base tile(s)")
	return bytes


def cliff_to_rotbytes(clifffilename):
	# Rotation for the second byte
	# Only cliffs are affected, ground textures are not rotated anyway
	# mask is 0x30 = 00110000, 0 = not rotated, 1 = 90°, 2 = 180°, 3 = 270
	try:
		cimg = Image.open(clifffilename)
	except FileNotFoundError:
		print("File %s not found"%clifffilename)
		return
	except Error:
		print("Error reading %s"%clifffilename)
		return
	cmode = cimg.mode
	width,height = cimg.size
	bytes = []
	for y in range(height-1):
		for x in range(width-1):
			if px_as_boolean(cimg.getpixel((x,y)), cmode):
				ncliff = y > 0 and px_as_boolean(cimg.getpixel((x,y-1)), cmode)
				scliff = y < height-2 and px_as_boolean(cimg.getpixel((x,y+1)), cmode)
				wcliff = x > 0 and px_as_boolean(cimg.getpixel((x-1,y)), cmode)
				ecliff = y < height-2 and px_as_boolean(cimg.getpixel((x+1,y)), cmode)
				if ncliff or scliff:
					bytes.append(0x20)
				else:
					bytes.append(0)
			else:
				bytes.append(0)
		# for x range end
	# for y range end
	return bytes

def find_gate(img, mode, startx, starty, width, height):
	gate = {"startx": startx, "starty": starty}
	x = startx
	y = starty
	endx = x
	endy = y
	if not px_as_boolean(img.getpixel((x,y)), mode):
		return None
	# Gates are only lines, not rectangles. Check the longest path.
	# Find gate width
	x = x+1
	while px_as_boolean(img.getpixel((x,starty)), mode) and x < width:
		x = x+1
	endx = x-1
	width = endx - startx
	# Find gate height
	y = y+1
	while px_as_boolean(img.getpixel((startx,y)), mode) and y < height:
		y = y+1
	endy = y-1
	height = endy - starty
	if width > height:
		gate['endx'] = endx
		gate['endy'] = starty
	else:
		gate['endx'] = startx
		gate['endy'] = endy
	return gate

def gatemap_to_gates(gatefilename):
	try:
		img = Image.open(gatefilename)
	except FileNotFoundError:
		print("File %s not found, ignoring gateways"%gatefilename)
		return []
	except Error:
		print("Error reading %s"%gatefilename)
		return
	mode = img.mode
	width,height = img.size
	gates = []
	px_read = {}
	print("Reading gatemap %s as %s" % (gatefilename, mode))
	for y in range(height-1):
		for x in range(width-1):
			if "%d-%d"%(x,y) in px_read:
				continue
			gate = find_gate(img, mode, x, y, width, height)
			if gate:
				gates.append(gate)
				for gx in range(gate["startx"], gate["endx"]+1):
					for gy in range(gate["starty"], gate["endy"]+1):
						px_read["%d-%d"%(gx,gy)] = True
			else:
				px_read["%d-%d"%(x,y)] = True
			# if gate end
		# for x range end
	# for y range end
	return gates


def write_header(output, width, height):
	"""Write the first bytes of the .map file in output"""
	output.write(b'\x6D\x61\x70\x20') # "map"
	output.write(b'\x0A\x00\x00\x00') # version
	output.write(num_to_32bits(width))
	output.write(num_to_32bits(height))
	return

def write_map(output, tilemap, heightmap, rotmap):
	"""Write the map content of the .map file in output"""
	for i in range(len(heightmap)):
		# see wz2100/lib/wzmaplib/include/wzmaplib/map.h for tile masks
		# tile num is 0-511, id is index*2+header in ttype.ttl
		output.write(tilemap[i].to_bytes(1,byteorder="little")) # texture
		output.write(rotmap[i].to_bytes(1,byteorder="little")) # rotation
		output.write((heightmap[i]).to_bytes(1,byteorder="little")) # height
	return

def write_gateways(output, gateways):
	"""Write the gateway map content of the .map file in output"""
	output.write(b'\x01\x00\x00\x00') # version
	output.write(num_to_32bits(len(gateways))) # count
	for gateway in gateways:
		output.write(gateway["startx"].to_bytes(1,byteorder="little"))
		output.write(gateway["starty"].to_bytes(1,byteorder="little"))
		output.write(gateway["endx"].to_bytes(1,byteorder="little"))
		output.write(gateway["endy"].to_bytes(1,byteorder="little"))
	return


def write_gam(output, width, height):
	"""Write the .gam file in output"""
	output.write(b'\x67\x61\x6D\x65') # "game"
	output.write(b'\x08\x00\x00\x00') # ???
	output.write(b'\x00\x00\x00\x00') # ???
	output.write(b'\x00\x00\x00\x00') # ???
	output.write(b'\x00\x00\x00\x00') # ???
	output.write(b'\x00\x00\x00\x00') # ???
	output.write(num_to_32bits(width))
	output.write(num_to_32bits(height))
	output.write(b'\x00\x00\x00\x00') # ???
	output.write(b'\x00\x00\x00\x00') # ???
	output.write(b'\x00\x00\x00\x00') # ???
	output.write(b'\x00\x00\x00\x00') # ???
	output.write(b'\x00\x00\x00\x00') # ???
	return

def write_lev(output, name, players, env):
	dataset = env_dataset[env[0]]
	output.write(("\nlevel   %s\n"%name))
	output.write("players %d\n"%players)
	output.write("type    14\n")
	output.write(("dataset %s\n")%dataset) # Set terrain type
	output.write(("game    \"multiplay/maps/%s.gam\"\n"%name))
	return

def autogen_cliffmap(heightfilename, step, outfilename):
	try:
		img = Image.open(heightfilename)
	except FileNotFoundError:
		print("File %s not found"%heightfilename)
		return
	except Error:
		print("Error reading %s"%heightfilename)
		return
	mode = img.mode
	width,height = img.size
	cliff = Image.new('RGBA', img.size)
	print("Reading heightmap %s as %s" % (heightfilename, mode))
	if mode != "RGB" and mode != "RGBA" and mode != "L":
		print("Cannot parse heightmap, accepting only RGB, RGBA or L (greyscale)")
		return
	for y in range(height-2):
		for x in range(width-2):
			px = img.getpixel((x, y))[0]
			pxx = img.getpixel((x+1, y))[0]
			pxy = img.getpixel((x, y+1))[0]
			pxxy = img.getpixel((x+1, y+1))[0]
			if (abs(px-pxx) >= step or abs(px-pxy) >= step or abs(px-pxxy) >= step):
				cliff.putpixel((x,y), (255,64,64,255))
			else:
				cliff.putpixel((x,y), (0,0,0,0))
		#end-for
	#end-for
	cliff.save(outfilename)
	return True


def get_base_dir(mapdir):
	if mapdir[0] == "/":
		return mapdir
	else:
		return os.path.join(os.getcwd(), mapdir)


def read_map_props(filepath):
	with open(filepath, 'r') as props_file:
		props = json.load(props_file)
	#open end
	return props

if len(sys.argv) < 2:
	print("Usage:")
	print("	wzmapcompiler.py mapdir")
	print("	wzmapcompiler.py autocliff [min step=%d] mapdir"%default_autocliff_diff)
	exit()

mapdir = sys.argv[1]
if (len(sys.argv) >= 2 and sys.argv[1] == "autocliff"):
	step = default_autocliff_diff
	mapdir = sys.argv[2]
	if (len(sys.argv) >= 4):
		step = int(argv[2])
		mapdir = argv[3]
	mapdir = get_base_dir(mapdir)
	if autogen_cliffmap(os.path.join(mapdir, "heightmap.png"), step, os.path.join(mapdir, "autocliffmap.png")):
		print("Done generating cliffmap into autocliffmap.png with step of %d."%step)
	exit()

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

if not ('width' in props) or not ('height' in props) or not ('players' in props) or not ('env' in props):
	print("Cannot read width, height, env and/or players from map.json")
	exit()

if not props['env'][0] in env_dataset:
	print("Environment not found, should be 'arizona' or 'rockies'")
	exit()

if not ('name' in props):
	props['name'] = os.path.basename(os.path.abspath(os.path.join(os.getcwd(), mapdir)))


os.makedirs(os.path.join(mapdir, "build", "multiplay", "maps", props['name']), exist_ok=True)

with open(os.path.join(mapdir, "build/multiplay/maps/%s/game.map"%props['name']), 'wb') as o:
	heightmap = heightmap_to_bytes(os.path.join(mapdir, "heightmap.png"))
	if not heightmap:
		exit()
	tilemap = tilemap_to_bytes(os.path.join(mapdir, "tilemap.png"), os.path.join(mapdir, "cliffmap.png"), props['env'])
	if not tilemap:
		exit()
	rotmap = cliff_to_rotbytes(os.path.join(mapdir, "cliffmap.png"))
	if not rotmap:
		exit()
	gates = gatemap_to_gates(os.path.join(mapdir, "gatemap.png"))
	if gates == None:
		exit()
	write_header(o, props['width'], props['height'])
	write_map(o, tilemap, heightmap, rotmap)
	write_gateways(o, gates)
	print("Done compiling game.map")
with open(os.path.join(mapdir, "build/multiplay/maps/%s.gam"%props['name']), 'wb') as o:
	write_gam(o, props['width'], props['height'])
	print("Done generating %s.gam"%props['name'])
with open(os.path.join(mapdir, "build/%s.addon.lev"%props['name']), 'w') as o:
	write_lev(o, props['name'], props['players'], props['env'])
	print("Done creating %s.addon.lev"%props['name'])
shutil.copyfile(os.path.join(mapdir, "droid.json"), os.path.join(mapdir, "build/multiplay/maps/%s/droid.json"%props['name']))
shutil.copyfile(os.path.join(mapdir, "feature.json"), os.path.join(mapdir, "build/multiplay/maps/%s/feature.json"%props['name']))
shutil.copyfile(os.path.join(mapdir, "struct.json"), os.path.join(mapdir, "build/multiplay/maps/%s/struct.json"%props['name']))
shutil.copyfile(os.path.join(mapdir, "ttypes.ttp"), os.path.join(mapdir, "build/multiplay/maps/%s/ttypes.ttp"%props['name']))
print("Copied ttypes.ttp, droid.json, feature.json and struct.json into multiplayer")

generated_files=[
	"%s.addon.lev"%props['name'],
	"multiplay/maps/%s.gam"%props['name'],
	"multiplay/maps/%s/game.map"%props['name'],
	"multiplay/maps/%s/ttypes.ttp"%props['name'],
	"multiplay/maps/%s/droid.json"%props['name'],
	"multiplay/maps/%s/feature.json"%props['name'],
	"multiplay/maps/%s/struct.json"%props['name'],
]

wzfilename = '%dc-%s.wz'%(props['players'], props['name'])
with zipfile.ZipFile(os.path.join(mapdir, wzfilename), 'w', zipfile.ZIP_DEFLATED) as wz:
	for f in generated_files:
		wz.write(os.path.join(mapdir, "build", f), f)
	print("Done creating %s"%wzfilename)

