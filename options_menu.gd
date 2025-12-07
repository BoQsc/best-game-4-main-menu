extends Control

signal back_pressed

@onready var fullscreen_check = $Panel/VBoxContainer/FullscreenCheck
@onready var quality_btn = $Panel/VBoxContainer/QualityButton

var quality_presets = ["Low", "Medium", "High"]
var quality_index = 2 # Default to High

func _ready():
	# Set the checkbox state based on the current window mode
	var mode = DisplayServer.window_get_mode()
	var is_fullscreen = (mode == DisplayServer.WINDOW_MODE_FULLSCREEN or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN)
	if fullscreen_check:
		fullscreen_check.button_pressed = is_fullscreen
	
	# Set initial quality text
	_update_quality_label()
	
	# Set initial volume slider value
	var master_idx = AudioServer.get_bus_index("Master")
	var current_db = AudioServer.get_bus_volume_db(master_idx)
	$Panel/VBoxContainer/HSlider.value = db_to_linear(current_db) * 100

func _update_quality_label():
	if quality_btn:
		quality_btn.text = "Quality: " + quality_presets[quality_index]

func _on_back_button_pressed():
	# Emit a signal so the Main Menu knows to hide this and show itself again
	back_pressed.emit()
	queue_free() # Remove the options menu

func _on_master_volume_changed(value):
	# Value is 0-100, normalize to 0-1
	var volume_linear = value / 100.0
	var master_idx = AudioServer.get_bus_index("Master")
	
	# Convert linear to dB and set
	AudioServer.set_bus_volume_db(master_idx, linear_to_db(volume_linear))

func _on_fullscreen_toggled(toggled_on):
	if toggled_on:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)

func _on_quality_pressed():
	# Cycle through presets: 0 -> 1 -> 2 -> 0
	quality_index = (quality_index + 1) % quality_presets.size()
	_update_quality_label()
	
	# Apply logic here (Placeholder)
	print("Quality changed to: ", quality_presets[quality_index])
	# Example:
	# if quality_index == 0:
	# 	RenderingServer.global_shader_parameter_set("quality_level", 0)
