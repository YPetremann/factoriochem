-- completely reset global.gui_demo_items because we need to add examples_i and delete old demo states that might not have
--	selectors, which will get rebuilt when needed
if not global.gui_demo_items.examples_i then global.gui_demo_items = {examples_i = 0} end
