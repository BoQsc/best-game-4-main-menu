extends Control

@onready var click_sound = $ClickSoundPlayer

func _ready():
	# Connect all buttons to the click sound
	var buttons = [
		$MainMenu/MarginContainer/TextureButton,
		$MainMenu/TextureButton5/HBoxContainer/MarginContainer/TextureButton,
		$MainMenu/TextureButton5/HBoxContainer/MarginContainer2/TextureButton2,
		$MainMenu/TextureButton5/HBoxContainer/MarginContainer3/TextureButton3,
		$MainMenu/TextureButton5/HBoxContainer/MarginContainer4/TextureButton4
	]
	
	for btn in buttons:
		if btn:
			btn.pressed.connect(_on_button_pressed)

func _on_button_pressed():
	if click_sound:
		click_sound.play()
