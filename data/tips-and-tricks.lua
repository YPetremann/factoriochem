-- Constants
local TIPS_AND_TRICKS_GRAPHICS_ROOT = GRAPHICS_ROOT.."tips-and-tricks/"
local ORDER_BYTE_BASE = string.byte("a") - 1


-- Tips and tricks
function add_tips_and_tricks_recursive(structure, indent, order)
	-- add this entry
	local name = structure.name
	local entry = {
		type = "tips-and-tricks-item",
		name = "factoriochem-"..name,
		category = "factoriochem",
		order = order,
		image = TIPS_AND_TRICKS_GRAPHICS_ROOT..name..".png",
		starting_status = structure.starting_status or "unlocked",
	}
	if indent == 0 then
		entry.is_title = true
	else
		entry.indent = indent
	end
	data:extend({entry})

	-- add children entries
	local children = structure.children
	if children then
		for i, child in ipairs(children) do
			add_tips_and_tricks_recursive(child, indent + 1, order..string.char(i + ORDER_BYTE_BASE))
		end
	end
end

local tips_and_tricks_structure = {
	name = "introduction",
	starting_status = "suggested",
	children = {{
		name = "buildings",
		starting_status = "suggested",
		children = {{
			name = "moleculifier",
		}},
	}, {
		name = "gui",
		children = {
			{name = "gui-io"},
			{name = "gui-selectors"},
			{name = "gui-demo"},
			{name = "gui-examples"},
			{name = "gui-tools"},
		},
	}, {
		name = "gui-periodic-table",
	}, {
		name = "gui-molecule-builder",
	}},
}

data:extend({{type = "tips-and-tricks-item-category", name = "factoriochem", order = "_"}})
add_tips_and_tricks_recursive(tips_and_tricks_structure, 0, "a")
