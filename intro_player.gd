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
var _was_mouse_pressed: bool = false
var _logo_fade_tween: Tween = null  # Store tween so we can kill it when skipping
var _main_tween: Tween = null  # Store main animation tween

func _ready():
	if GameData.skip_intro:
		_cleanup_nodes()
		return

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

func _process(_delta):
	# Allow skipping with left mouse click or Enter/Space
	# Using polling because SubViewports might not receive InputEvents automatically
	if not _sequence_finished and is_playing():
		var mouse_pressed = Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT)
		var ui_accept = Input.is_action_just_pressed("ui_accept")
		
		if (mouse_pressed and not _was_mouse_pressed) or ui_accept:
			_on_video_finished()
		
		_was_mouse_pressed = mouse_pressed

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
		_logo_fade_tween = create_tween()
		# Fade Logo from Invisible (0) to Visible (1) ON TOP of the video
		_logo_fade_tween.tween_property(best_game_logo, "modulate:a", 1.0, logo_fade_in_duration).set_trans(Tween.TRANS_SINE)

# TRIGGER 2: Video Ends -> Cut to Black -> Fade out Logo -> Fade out Overlay
func _on_video_finished():
	if _sequence_finished: return
	
	# Check if we're SKIPPING (video still playing) or video ended naturally
	var is_skipping = is_playing()
	
	# Sync music if skipping
	if is_skipping:
		# Kill video audio immediately
		volume_db = -80.0
		
		if music_player:
			var stream_len = get_stream_length()
			if stream_len > 0:
				music_player.seek(11.0 + stream_len)
		
		# IMPORTANT: Disconnect the finished signal to prevent it firing later
		if finished.is_connected(_on_video_finished):
			finished.disconnect(_on_video_finished)

	_sequence_finished = true
	
	# Kill any running fade-in tween
	if _logo_fade_tween and _logo_fade_tween.is_valid():
		_logo_fade_tween.kill()
	
	# === NATURAL END: Run the full animation sequence ===
	
	# 1. Ensure Overlay is Visible (It sits BEHIND the video)
	if fade_overlay:
		fade_overlay.visible = true
	
	# 2. Smoothly Hide the Video
	modulate.a = 0.0
	
	# FAILSAFE: If video ended before logo started fading in
	if not _logo_fade_started:
		if best_game_logo:
			best_game_logo.modulate.a = 1.0
	else:
		if best_game_logo:
			best_game_logo.modulate.a = 1.0
	
	_main_tween = create_tween()
	
	# 3. HOLD LOGO
	_main_tween.tween_interval(logo_hold_duration)
	
	# 4. FADE OUT LOGO
	if best_game_logo:
		_main_tween.tween_property(best_game_logo, "modulate:a", 0.0, logo_fade_out_duration).set_trans(Tween.TRANS_SINE)
		# CRITICAL: Hide logo immediately after fade to prevent any reappearance
		_main_tween.tween_callback(func(): best_game_logo.visible = false)
	
	# Allow clicking through
	_main_tween.tween_callback(func(): 
		if fade_overlay: fade_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
		if intro_container: intro_container.mouse_filter = Control.MOUSE_FILTER_IGNORE
	)
	
	# 5. FADE OUT OVERLAY
	if fade_overlay:
		_main_tween.tween_property(fade_overlay, "modulate:a", 0.0, menu_reveal_duration).set_trans(Tween.TRANS_SINE)
	
	# 6. CLEANUP
	_main_tween.tween_callback(_cleanup_nodes)

func _cleanup_nodes():
	# Kill any running tweens first
	if _main_tween and _main_tween.is_valid():
		_main_tween.kill()
	if _logo_fade_tween and _logo_fade_tween.is_valid():
		_logo_fade_tween.kill()
	
	# Force logo to be fully invisible
	if best_game_logo:
		best_game_logo.modulate.a = 0.0
		best_game_logo.visible = false
	if intro_container:
		intro_container.visible = false
	if fade_overlay:
		fade_overlay.visible = false
	stop()
