extends Control

signal back_pressed

@onready var credits_text = $CreditsText
@onready var back_button = $BackButton

# Configuration
var auto_scroll_speed = 60.0 # Pixels per second
var is_auto_scrolling = true

func _ready():
	# Allow the scroll bar to work
	pass

func _process(delta):
	if is_auto_scrolling:
		# Generally, we modify the scrollbar value for smooth auto-scrolling
		var v_scroll = credits_text.get_v_scroll_bar()
		if v_scroll:
			v_scroll.value += auto_scroll_speed * delta

func _input(event):
	# If user uses mouse wheel or drags, stop auto scrolling
	if event is InputEventMouseButton:
		if event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
			is_auto_scrolling = false
			
	if event is InputEventMouseMotion:
		# Check if dragging scrollbar? Hard to detect easily without intricate signal logic.
		# Simplest: Any click stops it.
		if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
			is_auto_scrolling = false

func _on_back_button_pressed():
	back_pressed.emit()
	queue_free()
