extends VideoStreamPlayer

# --- ASSIGN THESE IN THE INSPECTOR ---
@export_group("Nodes")
@export var fade_overlay: ColorRect        
@export var intro_container: TextureRect   
@export var best_game_logo: CanvasItem        
@export var music_player: AudioStreamPlayer

@export_group("Animation Settings")
@export var logo_fade_in_duration: float = 1.0   # How fast logo appears over video
@export var logo_hold_duration: float = 1.0      # How long logo sits on black screen
@export var logo_fade_out_duration: float = 1.0  # How fast logo disappears
@export var menu_reveal_duration: float = 2.0    # How fast black screen fades to menu

# Start showing the logo this many seconds before the video ends
@export var transition_lead_time: float = 1.5

var _logo_fade_started: bool = false
var _sequence_finished: bool = false

func _ready():
	if music_player:
		music_player.play(11.0)

	finished.connect(_on_video_finished)
	
	# SETUP INITIAL STATES:
	
	# 1. Overlay: Hidden initially (prevent interference during video)
	if fade_overlay:
		fade_overlay.visible = false
		fade_overlay.color = Color.BLACK
		fade_overlay.modulate.a = 1.0 
	
	# 2. Video: Fully Visible
	modulate.a = 1.0
	
	# 3. Logo: INVISIBLE (Sitting ON TOP of the video)
	if best_game_logo:
		best_game_logo.modulate.a = 0.0 # Start invisible!

func _input(event):
	# Allow skipping with left mouse click or Enter/Space
	if not _sequence_finished and is_playing():
		if (event is InputEventMouseButton and event.pressed) or event.is_action_pressed("ui_accept"):
			# Jump straight to the end sequence
			_on_video_finished()

func _process(_delta):
	# Monitor time to trigger the Logo Fade In
	if not is_playing() or _logo_fade_started:
		return

	var stream_len = get_stream_length()
	if stream_len <= 0: return

	var time_remaining = stream_len - get_stream_position()

	# TRIGGER 1: Fade Logo IN (While video is still playing)
	if time_remaining <= transition_lead_time:
		_start_logo_appearance()

func _start_logo_appearance():
	_logo_fade_started = true
	
	if fade_overlay:
		fade_overlay.visible = true
	
	if best_game_logo:
		var tween = create_tween()
		# Fade Logo from Invisible (0) to Visible (1) ON TOP of the video
		tween.tween_property(best_game_logo, "modulate:a", 1.0, logo_fade_in_duration).set_trans(Tween.TRANS_SINE)

# TRIGGER 2: Video Ends -> Cut to Black -> Fade out Logo -> Fade out Overlay
func _on_video_finished():
	if _sequence_finished: return
	_sequence_finished = true
	
	# 1. Ensure Overlay is Visible (It sits BEHIND the video)
	if fade_overlay:
		fade_overlay.visible = true
	
	# 2. Smoothly Hide the Video (Use modulate instead of visible to avoid blinking)
	# This reveals the Black Overlay underneath, but the Logo remains visible on top
	modulate.a = 0.0
	
	# FAILSAFE: If video ended before logo started fading in (e.g. video too short),
	# force start the sequence so we don't get stuck in a weird state.
	if not _logo_fade_started:
		if best_game_logo:
			best_game_logo.modulate.a = 1.0 # Force visible immediately
	
	var tween = create_tween()
	
	# 3. HOLD LOGO (It is now sitting on the Black Overlay)
	tween.tween_interval(logo_hold_duration)
	
	# 4. FADE OUT LOGO (Revealing just the Black Overlay)
	if best_game_logo:
		tween.tween_property(best_game_logo, "modulate:a", 0.0, logo_fade_out_duration).set_trans(Tween.TRANS_SINE)
	
	# Allow clicking through just before the fade starts
	tween.tween_callback(func(): 
		if fade_overlay: fade_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
		if intro_container: intro_container.mouse_filter = Control.MOUSE_FILTER_IGNORE
	)
	
	# 5. FADE OUT OVERLAY (Revealing the Menu)
	if fade_overlay:
		tween.tween_property(fade_overlay, "modulate:a", 0.0, menu_reveal_duration).set_trans(Tween.TRANS_SINE)
	
	# 6. CLEANUP
	tween.tween_callback(_cleanup_nodes)

func _cleanup_nodes():
	if intro_container:
		intro_container.visible = false
	if fade_overlay:
		fade_overlay.visible = false
	stop()
