extends Control

@onready var click_sound = $ClickSoundPlayer

# Preload the options menu scene
var options_scene = preload("res://options_menu.tscn")
var credits_scene = preload("res://credits_menu.tscn")

# Define button paths
@onready var steam_btn = $MainMenu/MarginContainer/SteamButton
@onready var play_btn = $MainMenu/TextureButton5/HBoxContainer/MarginContainer/TextureButton
@onready var options_btn = $MainMenu/TextureButton5/HBoxContainer/MarginContainer2/TextureButton2
@onready var credits_btn = $MainMenu/TextureButton5/HBoxContainer/MarginContainer3/TextureButton3
@onready var quit_btn = $MainMenu/TextureButton5/HBoxContainer/MarginContainer4/TextureButton4
@onready var main_menu_container = $MainMenu

func _ready():
	# Connect buttons to their specific functions
	if steam_btn:
		steam_btn.pressed.connect(_on_steam_pressed)
	if play_btn:
		play_btn.pressed.connect(_on_play_pressed)
	if options_btn:
		options_btn.pressed.connect(_on_options_pressed)
	if credits_btn:
		credits_btn.pressed.connect(_on_credits_pressed)
	if quit_btn:
		quit_btn.pressed.connect(_on_quit_pressed)
	
	# Connect all buttons to sound effect
	var buttons = [steam_btn, play_btn, options_btn, credits_btn, quit_btn]
	for btn in buttons:
		if btn:
			btn.pressed.connect(_play_click_sound)

func _play_click_sound():
	if click_sound:
		click_sound.play()

func _on_steam_pressed():
	OS.shell_open("https://steamcommunity.com/id/boqsc/")

func _on_play_pressed():
	print("Play pressed! - Add scene change logic here")
	# Example: get_tree().change_scene_to_file("res://game_scene.tscn")

func _on_options_pressed():
	var options_instance = options_scene.instantiate()
	add_child(options_instance)
	
	# Listen for when the back button is pressed in the options menu
	options_instance.back_pressed.connect(_on_options_closed)
	
	# Hide the main menu while options are open
	main_menu_container.visible = false

func _on_options_closed():
	# Show the main menu again
	main_menu_container.visible = true

func _on_credits_pressed():
	var credits_instance = credits_scene.instantiate()
	add_child(credits_instance)
	
	# Listen for when the back button is pressed in the credits menu
	credits_instance.back_pressed.connect(_on_credits_closed)
	
	# Hide the main menu while credits are open
	main_menu_container.visible = false

func _on_credits_closed():
	# Show the main menu again
	main_menu_container.visible = true

func _on_quit_pressed():
	get_tree().quit()
