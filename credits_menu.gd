extends Control

signal back_pressed

@onready var credits_text = $CreditsText
@onready var back_button = $BackButton

# Configuration
var scroll_speed = 60.0
var speed_multiplier = 5.0
var start_y_offset = 0.0

func _ready():
	# Start the text below the screen
	start_y_offset = get_viewport_rect().size.y
	credits_text.position.y = start_y_offset
	
	# Ensure the label is tall enough to render everything so we can measure it
	# (fit_content in the scene usually handles height, but we need to move the node)
	pass

func _process(delta):
	var speed = scroll_speed
	
	# Speed up if holding click or interacting (simulated by checking action if defined, or just mouse)
	if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT) or Input.is_action_pressed("ui_accept"):
		speed *= speed_multiplier
		
	credits_text.position.y -= speed * delta
	
	# Check if text has scrolled completely off screen
	# The text height can be retrieved from get_content_height() for RichTextLabel
	var text_height = credits_text.get_content_height()
	
	if credits_text.position.y < -text_height:
		# Loop back or stop? Let's loop for now, or just stop.
		# Looping:
		credits_text.position.y = start_y_offset

func _on_back_button_pressed():
	back_pressed.emit()
	queue_free()
