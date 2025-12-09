extends Node

# Signal when a save is completed or loaded if needed
signal game_saved
signal game_loaded

const SAVE_DIR = "user://saves/"
var skip_intro: bool = false

func _ready():
	DirAccess.make_dir_absolute(SAVE_DIR)

func get_save_path(slot_id: int) -> String:
	return SAVE_DIR + "save_slot_" + str(slot_id) + ".dat"

func save_exists(slot_id: int) -> bool:
	return FileAccess.file_exists(get_save_path(slot_id))

func get_save_info(slot_id: int) -> Dictionary:
	if not save_exists(slot_id):
		return {}
	
	# Open file to read metadata (simplified for now, just returning file time)
	# In a real scenario, you'd store a Dictionary at the start of the file with 'player_name', 'time_played', etc.
	var file = FileAccess.open(get_save_path(slot_id), FileAccess.READ)
	if not file:
		return {}
		
	var data = file.get_var()
	if data is Dictionary:
		return data.get("metadata", {})
	
	return {}

func save_game(slot_id: int, game_state: Dictionary):
	var path = get_save_path(slot_id)
	var file = FileAccess.open(path, FileAccess.WRITE)
	if file:
		# Wrap state in a dictionary with metadata
		var full_data = {
			"metadata": {
				"timestamp": Time.get_datetime_string_from_system(),
				"slot_id": slot_id
			},
			"game_state": game_state
		}
		file.store_var(full_data)
		emit_signal("game_saved")
		print("Game saved to " + path)
	else:
		printerr("Failed to save game to " + path)

func load_game(slot_id: int) -> Dictionary:
	if not save_exists(slot_id):
		return {}
		
	var path = get_save_path(slot_id)
	var file = FileAccess.open(path, FileAccess.READ)
	if file:
		var full_data = file.get_var()
		emit_signal("game_loaded")
		if full_data is Dictionary and full_data.has("game_state"):
			return full_data["game_state"]
		return full_data # Fallback for older format if any
	return {}

func delete_save(slot_id: int):
	if save_exists(slot_id):
		var dir = DirAccess.open(SAVE_DIR)
		dir.remove(get_save_path(slot_id))
		print("Deleted save slot " + str(slot_id))
