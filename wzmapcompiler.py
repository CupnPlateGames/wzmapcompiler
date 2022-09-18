from PIL import Image
import zipfile
import os, sys, shutil

# RGB codes to tile index
default_tiledef = {
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
# Regular tile index to cliff tile index 
default_cliffdef = {
	# Rocky cliffs
	5: 46, # gravel to gravel cliff
	41: 44, # gravel snow to gravel snow cliff
	23: 29, # grass snow to grass snow cliff
	64: 76 # snow to snow cliff
}
default_cliff = 46
default_autocliff_diff = 50 # roughly 35°


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


def px_to_tile(px):
	"""Get the tile index from a pixel color"""
	rgb = (px[0], px[1], px[2])
	if not rgb in default_tiledef:
		return
	return default_tiledef[rgb]

def tile_to_cliff(t):
	"""Get the cliff tile index from a tile index"""
	if not t in default_cliffdef:
		return
	return default_cliffdef[t]

def is_px_cliff(px, mode):
	if mode == "RGBA":
		return px[3] > 16 # alpha detection
	elif mode == "RGB":
		return px[0] + px[1] + px[2] > 16 # not black
	else:
		return px[0] > 16 # not black either

def tilemap_to_bytes(tilefilename, clifffilename):
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
	for y in range(height-1):
		for x in range(width-1):
			px = timg.getpixel((x, y))
			tile = px_to_tile(px)
			cpx = cimg.getpixel((x,y))
			iscliff = is_px_cliff(cpx, cmode)
			if not tile:
				if iscliff:
					bytes.append(default_cliff)
				else:
					bytes.append(0)
				terror = True
			else:
				if iscliff:
					tile = tile_to_cliff(tile)
				if not tile:
					bytes.append(default_cliff)
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
			if is_px_cliff(cimg.getpixel((x,y)), cmode):
				ncliff = y > 0 and is_px_cliff(cimg.getpixel((x,y-1)), cmode)
				scliff = y < height-2 and is_px_cliff(cimg.getpixel((x,y+1)), cmode)
				wcliff = x > 0 and is_px_cliff(cimg.getpixel((x-1,y)), cmode)
				ecliff = y < height-2 and is_px_cliff(cimg.getpixel((x+1,y)), cmode)
				if ncliff or scliff:
					bytes.append(0x20)
				else:
					bytes.append(0)
			else:
				bytes.append(0)
		# for x range end
	# for y range end
	return bytes


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
	print("Gateways not currently supported, emptying")
	output.write(b'\x01\x00\x00\x00') # version
	output.write(b'\x00\x00\x00\x00') # count
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

def write_lev(output, name):
	types = [14,18,19]
	for i in range(3):
		output.write(("\nlevel   %s-T%i\n"%(name,i+1)))
		output.write("players 2\n")
		output.write(("type    %d\n"%types[i]))
		output.write("dataset MULTI_CAM_3\n") # Set terrain type 3=rockies
		output.write(("game    \"multiplay/maps/%s.gam\"\n"%name))
		#output.write("data    \"wrf/multi/skirmish2.wrf\"\n")
		#output.write("data    \"wrf/multi/fog3.wrf\"\n")
	#end-for
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



if len(sys.argv) < 2:
	print("Usage:")
	print("	wzmapcompiler.py width height")
	print("	wzmapcompiler.py autocliff [min step=%d]")
	exit()

if (len(sys.argv) >= 2 and sys.argv[1] == "autocliff"):
	step = default_autocliff_diff
	if (len(sys.argv) >= 3):
		step = int(argv[2])
	if autogen_cliffmap("./heightmap.png", step, "./autocliffmap.png"):
		print("Done generating cliffmap into autocliffmap.png with step of %d."%step)
	exit()

width = int(sys.argv[1])
height = int(sys.argv[2])

map_name = os.path.basename(os.getcwd())
os.makedirs(os.path.join("build", "multiplay", "maps", map_name), exist_ok=True)

with open("./build/multiplay/maps/%s/game.map"%map_name, 'wb') as o:
	heightmap = heightmap_to_bytes("./heightmap.png")
	if not heightmap:
		exit()
	tilemap = tilemap_to_bytes("./tilemap.png", "./cliffmap.png")
	if not tilemap:
		exit()
	rotmap = cliff_to_rotbytes("./cliffmap.png")
	if not rotmap:
		exit()
	write_header(o, width, height)
	write_map(o, tilemap, heightmap, rotmap)
	write_gateways(o, None)
	print("Done compiling game.map")
with open("./build/multiplay/maps/%s.gam"%map_name, 'wb') as o:
	write_gam(o, width, height)
	print("Done generating %s.gam"%map_name)
with open("./build/%s.addon.lev"%map_name, 'w') as o:
	write_lev(o, map_name)
	print("Done creating %s.addon.lev"%map_name)
shutil.copyfile("./droid.json", "./build/multiplay/maps/%s/droid.json"%map_name)
shutil.copyfile("./feature.json", "./build/multiplay/maps/%s/feature.json"%map_name)
shutil.copyfile("./struct.json", "./build/multiplay/maps/%s/struct.json"%map_name)
shutil.copyfile("./ttypes.ttp", "./build/multiplay/maps/%s/ttypes.ttp"%map_name)
print("Copied ttypes.ttp, droid.json, feature.json and struct.json into multiplayer")

generated_files=[
	"%s.addon.lev"%map_name,
	"multiplay/maps/%s.gam"%map_name,
	"multiplay/maps/%s/game.map"%map_name,
	"multiplay/maps/%s/ttypes.ttp"%map_name,
	"multiplay/maps/%s/droid.json"%map_name,
	"multiplay/maps/%s/feature.json"%map_name,
	"multiplay/maps/%s/struct.json"%map_name,
]
	
with zipfile.ZipFile('%s.wz'%map_name, 'w', zipfile.ZIP_DEFLATED) as wz:
	for f in generated_files:
		wz.write(os.path.join("build", f), f)
	print("Done creating %s.wz"%map_name)

