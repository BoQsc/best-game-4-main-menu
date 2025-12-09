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
@onready var donate_btn = $MainMenu/TextureButton5/MarginContainer2/DonateButton
@onready var discord_btn = $MainMenu/TextureButton5/MarginContainer3/DiscordButton

func _ready():
	# Set custom mouse cursor (scaled down by 85% -> 0.15 size)
	var cursor_texture = load("res://main_menu_mouse_cursor.png")
	if cursor_texture:
		var image = cursor_texture.get_image()
		var new_size = Vector2(image.get_width(), image.get_height()) * 0.20
		image.resize(int(new_size.x), int(new_size.y))
		var scaled_texture = ImageTexture.create_from_image(image)
		
		# Set cursor with hotspot at top-left (default)
		Input.set_custom_mouse_cursor(scaled_texture)
		
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
	if donate_btn:
		donate_btn.pressed.connect(_on_donate_pressed)
	if discord_btn:
		discord_btn.pressed.connect(_on_discord_pressed)
	
	# Connect all buttons to sound effect
	var buttons = [steam_btn, play_btn, options_btn, credits_btn, quit_btn, donate_btn, discord_btn]
	for btn in buttons:
		if btn:
			btn.pressed.connect(_play_click_sound)

func _play_click_sound():
	if click_sound:
		click_sound.play()

func _on_steam_pressed():
	OS.shell_open("https://steamcommunity.com/id/boqsc/")

func _on_donate_pressed():
	OS.shell_open("https://opencollective.com/boqsc")

func _on_discord_pressed():
	OS.shell_open("https://discord.com/invite/tPBJXU7B6C")

@onready var save_slot_menu_scene = preload("res://play_menu/save_slot_menu.tscn")

func _on_play_pressed():
	if save_slot_menu_scene:
		var menu_instance = save_slot_menu_scene.instantiate()
		add_child(menu_instance)
		menu_instance.back_pressed.connect(_on_save_menu_closed)
		main_menu_container.visible = false

func _on_save_menu_closed():
	main_menu_container.visible = true

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
