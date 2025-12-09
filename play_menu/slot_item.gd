extends PanelContainer

var slot_id: int = -1

@onready var label = $HBoxContainer/Label
@onready var play_button = $HBoxContainer/PlayButton
@onready var delete_button = $HBoxContainer/DeleteButton

func _ready():
	play_button.pressed.connect(_on_play_pressed)
	delete_button.pressed.connect(_on_delete_pressed)

func setup_slot(id: int):
	slot_id = id
	refresh_ui()

func refresh_ui():
	if slot_id == -1: return
	
	var info = GameData.get_save_info(slot_id)
	if info.is_empty():
		label.text = "Slot " + str(slot_id) + " (Empty)"
		play_button.text = "New Game"
		delete_button.disabled = true
	else:
		var time = info.get("timestamp", "Unknown Time")
		label.text = "Slot " + str(slot_id) + " - " + time
		play_button.text = "Load"
		delete_button.disabled = false

func _on_play_pressed():
	# Notify parent menu
	# We can't rely on 'owner' always being the script if instanced dynamically in some ways, but here it's fine
	# But better to emit signal or call parent function if defined.
	# The parent script expects to handle validation.
	# Actually, the parent script `save_slot_menu.gd` calls `_on_slot_selected`.
	# I'll emit a signal or call up.
	
	var menu = find_parent("SaveSlotMenu")
	if menu and menu.has_method("_on_slot_selected"):
		menu._on_slot_selected(slot_id)

func _on_delete_pressed():
	GameData.delete_save(slot_id)
	refresh_ui()
