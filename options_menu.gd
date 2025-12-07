extends Control

signal back_pressed

@onready var fullscreen_check = $Panel/VBoxContainer/FullscreenCheck

func _ready():
	# Set the checkbox state based on the current window mode
	var mode = DisplayServer.window_get_mode()
	var is_fullscreen = (mode == DisplayServer.WINDOW_MODE_FULLSCREEN or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN)
	if fullscreen_check:
		fullscreen_check.button_pressed = is_fullscreen

func _on_back_button_pressed():
	# Emit a signal so the Main Menu knows to hide this and show itself again
	back_pressed.emit()
	queue_free() # Remove the options menu

func _on_fullscreen_toggled(toggled_on):
	if toggled_on:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
