extends Control

signal back_pressed

# Preload the game scene (Using main_menu.tscn as placeholder but logically should be the game)
# We need to transition to the loading screen which then loads the game
const LOADING_SCREEN_PATH = "res://play_menu/loading_screen.tscn"
const GAME_SCENE_PATH = "res://node_2d.tscn" # Placeholder: Assuming current scene is main menu, but usually we load a different "Game" scene. 
# Since user said "Main Game Scene" and "Marching Cubes", I will assume we might need a placeholder or just reload for now
# Actually, the user wants to go TO the game. 
# I'll define the target scene here. Ideally this should be passed or global.
var target_game_scene = "res://world.tscn" # We don't have this yet, checking existing files...

# Wait, the current open file is "node_2d.tscn" which IS the main menu.
# I need to know what the GAME scene is. 
# Based on user context "working on main game scene", it might be a different file not in the list or "node_2d.tscn" IS the menu.
# I'll use a placeholder "res://game_world.tscn" and comment it.

@onready var slot_list = $Panel/VBoxContainer
# Use specific node paths for slots if static, or generate dynamically.
# For simplicity, I will create 3 static buttons in the Tscn.

func _ready():
	_refresh_slots()

func _refresh_slots():
	# Loop through children of slot_list (assuming they are buttons/panels for slots)
	for i in range(slot_list.get_child_count()):
		var slot_node = slot_list.get_child(i)
		if slot_node.has_method("setup_slot"):
			slot_node.setup_slot(i + 1) # Slot IDs 1-based

func _on_back_pressed():
	back_pressed.emit()
	queue_free()

func _on_slot_selected(slot_id):
	# Trigger loading process
	print("Selected Slot: ", slot_id)
	
	# Pass data to loading screen (via a global or scene args)
	# Since LoadingScreen isn't an Autoload, we instantiate it or change scene to it.
	# We should probably change scene to LoadingScreen and tell IT what to load.
	
	var loading_screen = load(LOADING_SCREEN_PATH).instantiate()
	loading_screen.target_scene_path = target_game_scene # The game world
	loading_screen.save_slot_id = slot_id
	
	# Current simple approach: Change scene to loading screen
	# Only problem: We can't pass properties to `change_scene_to_file`.
	# So we usually use a global variable or instantiate and set root.
	
	# Better approach for Godot:
	# 1. Get SceneTree.
	# 2. Switch current scene to LoadingScreen instance.
	
	get_tree().root.add_child(loading_screen)
	get_tree().current_scene.queue_free() # Remove Main Menu
	get_tree().current_scene = loading_screen
