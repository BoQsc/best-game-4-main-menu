extends Control

signal back_pressed

func _on_back_button_pressed():
	# Emit a signal so the Main Menu knows to hide this and show itself again
	back_pressed.emit()
	queue_free() # Remove the credits menu
