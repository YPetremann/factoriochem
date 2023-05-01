data:extend({
	{
		type = "int-setting",
		name = "factoriochem-building-ticks-per-update",
		setting_type = "runtime-global",
		default_value = 10,
		minimum_value = 1,
		maximum_value = 60,
		order = "a",
	},
	{
		type = "int-setting",
		name = "factoriochem-detector-ticks-per-update",
		setting_type = "runtime-global",
		default_value = 1,
		minimum_value = 1,
		maximum_value = 60,
		order = "b",
	},
	{
		type = "bool-setting",
		name = "factoriochem-allow-complex-molecules",
		setting_type = "runtime-global",
		default_value = true,
		order = "c",
	},
	{
		type = "bool-setting",
		name = "factoriochem-compatibility-mode",
		setting_type = "startup",
		default_value = false,
		order = "d",
	},
})
