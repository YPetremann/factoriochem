import os
import cv2
import numpy
import math


#Constants
MAX_GRID_WIDTH = 3
MAX_GRID_HEIGHT = 3
BASE_ICON_SIZE = 64
BASE_ICON_MIPS = 3
COLOR_FOR_BONDS = [
	(192, 240, 192, 0),
	(240, 240, 240, 0),
	(176, 176, 240, 0),
	(240, 176, 176, 0),
	(176, 176, 176, 0),
]
ATOM_ROWS = [
	#Row 1
	["H", "He"],
	#Row 2
	["Li", "Be", "B", "C", "N", "O", "F", "Ne"],
	#Row 3
	["Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar"],
	#Row 4
	["K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr"],
	#Row 5
	["Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe"],
	#Row 6
	[
		"Cs", "Ba",
		"La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
		"Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn",
	],
	#Row 7
	[
		"Fr", "Ra",
		"Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No",
		"Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
	],
]
RADIUS_FRACTION = 30 / 64
PRECISION_BITS = 8
PRECISION_MULTIPLIER = 1 << PRECISION_BITS
CIRCLE_DATA = {}
HCNO = ["H", "C", "N", "O"]
MAX_ATOMS_HCNO = 8
MAX_ATOMS_Ne = 4
MAX_ATOMS_Ar = 3
MAX_ATOMS_OTHER = 2
MAX_SINGLE_BONDS = 2
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE_FRACTIONS = [0, 1.25 / 64, 1 / 64]
FONT_THICKNESS_FRACTION = 2 / 64
TEXT_COLOR = (0, 0, 0, 0)
TEXT_DATAS = {}
BOND_COLOR = (0, 0, 0, 0)
BOND_LENGTH_FRACTIONS = [0, 12 / 64, 12 / 64]
BOND_THICKNESS_FRACTION = 6 / 64
BOND_SPACING_FRACTION = 18 / 64
ITEM_GROUP_SIZE = 128
ITEM_GROUP_MIPS = 2


#Utility functions
def filled_mip_image(base_size, mips, color):
	return numpy.full((base_size, sum(base_size >> i for i in range(mips)), 4), color, numpy.uint8)

def draw_alpha_on(image, draw):
	mask = numpy.zeros(image.shape[:2], numpy.uint8)
	draw(mask)
	mask_section = mask > 0
	image[:, :, 3][mask_section] = mask[mask_section]
	return mask


#Sub-image generation
def get_circle_mip_datas(base_size, y_scale, x_scale, y, x, mips):
	base_size_data = CIRCLE_DATA.get(base_size, None)
	if not base_size_data:
		base_size_data = {}
		CIRCLE_DATA[base_size] = base_size_data
	y_scale_data = base_size_data.get(y_scale, None)
	if not y_scale_data:
		y_scale_data = {}
		base_size_data[y_scale] = y_scale_data
	scale_data = y_scale_data.get(x_scale, None)
	if not scale_data:
		scale = max(x_scale, y_scale)
		scale_data = {
			"scale": scale,
			"radius": base_size * RADIUS_FRACTION / scale,
			"center_y_min": 0.5 * (1 + scale - y_scale),
			"center_x_min": 0.5 * (1 + scale - x_scale),
		}
		y_scale_data[x_scale] = scale_data
	y_data = scale_data.get(y, None)
	if not y_data:
		y_data = {}
		scale_data[y] = y_data
	mip_datas = y_data.get(x, None)
	if mip_datas:
		return mip_datas
	mip_datas = {}
	y_data[x] = mip_datas
	center_y = base_size * (y + scale_data["center_y_min"]) / scale_data["scale"]
	center_x = base_size * (x + scale_data["center_x_min"]) / scale_data["scale"]
	for mip in range(mips):
		size = base_size >> mip
		alpha = numpy.zeros((size, size), numpy.uint8)
		shrink = 1 / (1 << mip)
		mip_center_x = center_x * shrink
		mip_center_y = center_y * shrink
		draw_center_x = round((mip_center_x - 0.5) * PRECISION_MULTIPLIER)
		draw_center_y = round((mip_center_y - 0.5) * PRECISION_MULTIPLIER)
		draw_radius = round((scale_data["radius"] * shrink - 0.5) * PRECISION_MULTIPLIER)
		cv2.circle(alpha, (draw_center_x, draw_center_y), draw_radius, 255, -1, cv2.LINE_AA, PRECISION_BITS)
		mip_datas[mip] = {
			"alpha": alpha,
			"center_x": mip_center_x,
			"center_y": mip_center_y,
		}
	return mip_datas

def get_text_data(symbol, base_size, mips):
	base_size_data = TEXT_DATAS.get(base_size, None)
	if not base_size_data:
		base_size_data = {}
		TEXT_DATAS[base_size] = base_size_data
	text_data = base_size_data.get(symbol, None)
	if text_data:
		return text_data
	font_scale = FONT_SCALE_FRACTIONS[len(symbol)] * base_size
	font_thickness = int(FONT_THICKNESS_FRACTION * base_size)
	((text_width, text_height), _) = cv2.getTextSize(symbol, FONT, font_scale, font_thickness)
	#add a buffer in all directions so that we can adjust what part of the image we resize for a given
	#	mip/scale
	text_buffer_border = 1 << (mips - 1)
	for scale in range(2, max(MAX_GRID_WIDTH, MAX_GRID_HEIGHT) + 1):
		text_buffer_border = text_buffer_border * scale // math.gcd(text_buffer_border, scale)
	text_full_width = text_width + text_buffer_border * 2
	text_full_height = text_height + font_thickness * 3 + text_buffer_border * 2
	text_bottom_left = (text_buffer_border, text_buffer_border + text_height + font_thickness)
	text = numpy.full((text_full_height, text_full_width, 4), TEXT_COLOR, numpy.uint8)
	text_mask = draw_alpha_on(
		text,
		lambda mask: cv2.putText(mask, symbol, text_bottom_left, FONT, font_scale, 255, font_thickness, cv2.LINE_AA))

	#find the edges of the text
	for left_edge in range(text_full_width):
		if text_mask[:, left_edge].sum() > 0:
			break
	for top_edge in range(text_full_height):
		if text_mask[top_edge].sum() > 0:
			break
	for right_edge in range(text_full_width, -1, -1):
		if text_mask[:, right_edge - 1].sum() > 0:
			break
	for bottom_edge in range(text_full_height, -1, -1):
		if text_mask[bottom_edge - 1].sum() > 0:
			break
	text_data = {
		"image": text,
		"center_x": (left_edge + right_edge) / 2,
		"center_y": (top_edge + bottom_edge) / 2,
		"half_width": (right_edge - left_edge) / 2,
		"half_height": (bottom_edge - top_edge) / 2,
	}
	base_size_data[symbol] = text_data
	return text_data


#Generate atom images
def overlay_image(back_image, back_left, back_top, front_image, front_left, front_top, width, height):
	back_right = back_left + width
	back_bottom = back_top + height
	front_right = front_left + width
	front_bottom = front_top + height
	back_alpha = back_image[back_top:back_bottom, back_left:back_right, 3] / 255.0
	front_alpha = front_image[front_top:front_bottom, front_left:front_right, 3] / 255.0
	new_alpha = back_alpha + front_alpha * (1 - back_alpha)
	back_image[back_top:back_bottom, back_left:back_right, 3] = new_alpha * 255
	#prevent NaN issues on fully-transparent pixels
	new_alpha[new_alpha == 0] = 1
	for color in range(0, 3):
		back_color = back_image[back_top:back_bottom, back_left:back_right, color]
		front_color = front_image[front_top:front_bottom, front_left:front_right, color]
		back_image[back_top:back_bottom, back_left:back_right, color] = \
			back_color + (front_color * 1.0 - back_color) * front_alpha / new_alpha

def gen_single_atom_image(symbol, bonds, base_size, y_scale, x_scale, y, x, mips):
	#set the base color for this atom
	image = filled_mip_image(base_size, mips, COLOR_FOR_BONDS[bonds])
	place_x = 0
	mip_datas = get_circle_mip_datas(base_size, y_scale, x_scale, y, x, mips)
	scale = max(x_scale, y_scale)
	for mip in range(mips):
		#patch over the circle alpha mask for each mip
		size = base_size >> mip
		mip_data = mip_datas[mip]
		image[0:size, place_x:place_x + size, 3] = mip_data["alpha"]

		#overlay text by finding the best section to resize to match the target size and position
		#first determine the area we're going to draw to, in full pixel dimensions
		text_data = get_text_data(symbol, base_size, mips)
		text = text_data["image"]
		text_scale = scale << mip
		mip_center_x = place_x + mip_data["center_x"]
		text_dst_left = math.floor(mip_center_x - text_data["half_width"] / text_scale)
		text_dst_top = math.floor(mip_data["center_y"] - text_data["half_height"] / text_scale)
		text_dst_right = math.ceil(mip_center_x + text_data["half_width"] / text_scale)
		text_dst_bottom = math.ceil(mip_data["center_y"] + text_data["half_height"] / text_scale)
		text_dst_width = text_dst_right - text_dst_left
		text_dst_height = text_dst_bottom - text_dst_top

		#next, find the corresponding spot in the text image to retrieve, and in most cases, shrink the image to fit the
		#	area we're going to draw to
		text_src_left = round(text_data["center_x"] - (mip_center_x - text_dst_left) * text_scale)
		text_src_top = round(text_data["center_y"] - (mip_data["center_y"] - text_dst_top) * text_scale)
		if text_scale > 0:
			text_src_right = text_src_left + text_dst_width * text_scale
			text_src_bottom = text_src_top + text_dst_height * text_scale
			text_src = text[text_src_top:text_src_bottom, text_src_left:text_src_right]
			text = cv2.resize(text_src, (text_dst_width, text_dst_height), interpolation=cv2.INTER_AREA)
			text_src_left = 0
			text_src_top = 0

		#finally, overlay the text image over the atom image
		overlay_image(
			image, text_dst_left, text_dst_top, text, text_src_left, text_src_top, text_dst_width, text_dst_height)

		place_x += size
	return image

def gen_atom_images(symbol, bonds, molecule_max_atoms, base_size, mips):
	atom_folder = os.path.join("atoms", symbol)
	if not os.path.exists(atom_folder):
		os.makedirs(atom_folder)
	for y_scale in range(1, min(molecule_max_atoms, MAX_GRID_HEIGHT) + 1):
		for x_scale in range(1, min(molecule_max_atoms + 1 - y_scale, MAX_GRID_WIDTH) + 1):
			for y in range(y_scale):
				for x in range(x_scale):
					image = gen_single_atom_image(symbol, bonds, base_size, y_scale, x_scale, y, x, mips)
					file_name = os.path.join(atom_folder, f"{y_scale}{x_scale}{y}{x}.png")
					cv2.imwrite(file_name, image, [cv2.IMWRITE_PNG_COMPRESSION, 9])

def gen_all_atom_images(base_size, mips):
	element_number = 0
	last_element_number = 0
	for (atom_row_i, atom_row) in enumerate(ATOM_ROWS):
		last_element_number += len(atom_row)
		for (i, symbol) in enumerate(atom_row):
			element_number += 1
			if element_number >= last_element_number - 4:
				bonds = last_element_number - element_number
			elif element_number == last_element_number - 5:
				bonds = 3
			elif i < 2:
				bonds = i + 1
			else:
				bonds = 0
			if bonds == 0:
				molecule_max_atoms = 1
			elif atom_row_i > 2:
				molecule_max_atoms = MAX_ATOMS_OTHER
			elif atom_row_i == 2:
				molecule_max_atoms = MAX_ATOMS_Ar
			elif symbol in HCNO:
				molecule_max_atoms = MAX_ATOMS_HCNO
			else:
				molecule_max_atoms = MAX_ATOMS_Ne
			#larger-number atoms with many bonds can't fulfill all their bonds within their max atom count, so to
			#	save on images, treat them like they can only be single atoms, but still draw them with their
			#	right bond color
			molecule_min_atoms = math.ceil(bonds / MAX_SINGLE_BONDS) + 1
			if molecule_min_atoms > molecule_max_atoms:
				molecule_max_atoms = 1
			gen_atom_images(symbol, bonds, molecule_max_atoms, base_size, mips)
		print(f"Atom row {atom_row_i + 1} written")


#Generate bond images
def gen_bond_images(base_size, y_scale, x_scale, y, x, mips):
	#generate both L and U images at once
	#L bond images will use the original values, U bond images will use the inverse
	scale = max(x_scale, y_scale)
	scale_center_y_min = 0.5 * (1 + scale - y_scale)
	scale_center_x_min = 0.5 * (1 + scale - x_scale)
	center_y = base_size * (y + scale_center_y_min) / scale
	center_x = base_size * (x + scale_center_x_min - 0.5) / scale
	images = {"L": {}, "U": {}}
	for bond_count in range(1, 3):
		half_bond_length = BOND_LENGTH_FRACTIONS[bond_count] * base_size / scale * 0.5
		l = filled_mip_image(base_size, mips, BOND_COLOR)
		u = filled_mip_image(base_size, mips, BOND_COLOR)
		bond_spacing = int(BOND_SPACING_FRACTION * base_size / scale)
		center_y_min = center_y - bond_spacing * (bond_count - 1) / 2
		for bond in range(bond_count):
			draw_y = round((center_y_min + bond * bond_spacing - 0.5) * PRECISION_MULTIPLIER)
			draw_left = (round((center_x - half_bond_length - 0.5) * PRECISION_MULTIPLIER), draw_y)
			draw_right = (round((center_x + half_bond_length - 0.5) * PRECISION_MULTIPLIER), draw_y)
			bond_thickness = int(BOND_THICKNESS_FRACTION * base_size / scale)
			def draw(mask):
				cv2.line(mask, draw_left, draw_right, 255, bond_thickness, cv2.LINE_AA, PRECISION_BITS)
			draw_alpha_on(l, draw)
			draw_left = draw_left[::-1]
			draw_right = draw_right[::-1]
			draw_alpha_on(u, draw)
		place_x = 0
		l_mip_0 = l[:, 0:base_size]
		u_mip_0 = u[:, 0:base_size]
		for mip in range(1, mips):
			size = base_size >> mip
			place_x += base_size >> (mip - 1)
			#copy the entire image, performance isn't really an issue
			l[0:size, place_x:place_x + size] = cv2.resize(l_mip_0, (size, size), interpolation=cv2.INTER_AREA)
			u[0:size, place_x:place_x + size] = cv2.resize(u_mip_0, (size, size), interpolation=cv2.INTER_AREA)
		images["L"][bond_count] = l
		images["U"][bond_count] = u
	return images

def gen_and_write_bond_images(bond_folder, base_size, y_scale, x_scale, y, x, mips):
	#L and U images are identical only with X and Y swapped, so do them at the same time
	#generate "left" bonds: generate a bond only if x >= 1
	if x == 0:
		return
	name_specs = {"L": f"{y_scale}{x_scale}{y}{x}", "U":f"{x_scale}{y_scale}{x}{y}"}
	for (direction, bond_images) in gen_bond_images(base_size, y_scale, x_scale, y, x, mips).items():
		for (bonds, image) in bond_images.items():
			#file names represent left and up bonds for an atom with the same number set
			file_path = os.path.join(bond_folder, f"{direction}{name_specs[direction]}{bonds}.png")
			cv2.imwrite(file_path, image, [cv2.IMWRITE_PNG_COMPRESSION, 9])

def gen_all_bond_images(base_size, mips):
	bond_folder = "bonds"
	if not os.path.exists(bond_folder):
		os.mkdir(bond_folder)
	for y_scale in range(1, MAX_GRID_HEIGHT + 1):
		for x_scale in range(1, MAX_GRID_WIDTH + 1):
			for y in range(y_scale):
				for x in range(x_scale):
					gen_and_write_bond_images(bond_folder, base_size, y_scale, x_scale, y, x, mips)
	print("Bond images written")

#Generate the icon for the molecule item group
def gen_item_group_icon():
	image = filled_mip_image(ITEM_GROUP_SIZE, ITEM_GROUP_MIPS, (0, 0, 0, 0))
	shape = [
		["O", 1, "C", 2, "N"],
		[  1,      1,      1],
		["N", 1, "O", 0, "H"],
		[  1,      0,      0],
		["H", 0,  "", 0,  ""],
	]
	y_scale = (len(shape) + 1) // 2
	x_scale = len(shape[1])
	bonds = {"H": 1, "C": 4, "N": 3, "O": 2}
	scale = max(y_scale, x_scale)
	for row_i in range(0, len(shape), 2):
		row = shape[row_i]
		y = row_i // 2
		for col_i in range(0, len(row), 2):
			x = col_i // 2
			symbol = row[col_i]
			if symbol:
				atom_image = gen_single_atom_image(
					symbol, bonds[symbol], ITEM_GROUP_SIZE, y_scale, x_scale, y, x, ITEM_GROUP_MIPS)
				overlay_image(image, 0, 0, atom_image, 0, 0, image.shape[1], ITEM_GROUP_SIZE)
			if col_i > 0 and row[col_i - 1] > 0:
				left_up_bond_images = gen_bond_images(ITEM_GROUP_SIZE, y_scale, x_scale, y, x, ITEM_GROUP_MIPS)
				left_bond_image = left_up_bond_images["L"][row[col_i - 1]]
				overlay_image(image, 0, 0, left_bond_image, 0, 0, image.shape[1], ITEM_GROUP_SIZE)
			if row_i > 0 and shape[row_i - 1][x] > 0:
				left_up_bond_images = gen_bond_images(ITEM_GROUP_SIZE, x_scale, y_scale, x, y, ITEM_GROUP_MIPS)
				up_bond_image = left_up_bond_images["U"][shape[row_i - 1][x]]
				overlay_image(image, 0, 0, up_bond_image, 0, 0, image.shape[1], ITEM_GROUP_SIZE)
	cv2.imwrite("item_group.png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
	print("Item group written")

os.chdir(os.path.dirname(os.path.abspath(__file__)))
gen_all_atom_images(BASE_ICON_SIZE, BASE_ICON_MIPS)
gen_all_bond_images(BASE_ICON_SIZE, BASE_ICON_MIPS)
gen_item_group_icon()