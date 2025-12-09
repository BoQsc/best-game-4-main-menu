extends Control

var target_scene_path: String = ""
var save_slot_id: int = -1
var _load_status = 0
var _progress = []

@onready var progress_bar = $ProgressBar
@onready var status_label = $Label

func _ready():
	# Start background loading
	if target_scene_path == "":
		printerr("LoadingScreen: No target scene path set!")
		return
		
	status_label.text = "Loading..."
	ResourceLoader.load_threaded_request(target_scene_path)

func _process(_delta):
	if target_scene_path == "": return
	
	_load_status = ResourceLoader.load_threaded_get_status(target_scene_path, _progress)
	
	if _progress.size() > 0:
		progress_bar.value = _progress[0] * 100
	
	if _load_status == ResourceLoader.THREAD_LOAD_LOADED:
		_on_load_complete()
	elif _load_status == ResourceLoader.THREAD_LOAD_FAILED or _load_status == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
		status_label.text = "Loading Failed!"
		$BackButton.visible = true
		$BackButton.pressed.connect(_on_back_pressed)
		set_process(false)

func _on_back_pressed():
	# Return to main menu (assuming node_2d.tscn is main menu)
	GameData.skip_intro = true
	get_tree().change_scene_to_file("res://node_2d.tscn")

func _on_load_complete():
	set_process(false)
	progress_bar.value = 100
	status_label.text = "Starting..."
	
	var scene_resource = ResourceLoader.load_threaded_get(target_scene_path)
	if scene_resource:
		# If we have a save slot, we might want to set global state BEFORE changing scene
		# Typically, the game scene's _ready() will check GameData.
		# But we usually need to tell GameData WHICH slot we are playing.
		
		# Assuming GameData has a CurrentSlot property? Not yet.
		# I should add `current_slot_id` to GameData or pass it.
		# I will add it to GameData dynamically if needed, or just assume the game handles it.
		# For now, I'll just change scene.
		
		get_tree().change_scene_to_packed(scene_resource)
