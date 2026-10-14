from demo_creator.plan.schema import Scene, VoiceSettings
from demo_creator.runs.cache import scene_audio_hash, scene_video_hash


def test_audio_hash_changes_with_narration():
    v = VoiceSettings()
    a = scene_audio_hash(Scene(id="s", narration="hello"), v)
    b = scene_audio_hash(Scene(id="s", narration="hello world"), v)
    assert a != b


def test_video_hash_stable():
    scene = Scene(id="s", narration="x", start_url="/", steps=[])
    h1 = scene_video_hash(scene, base_url="http://x", audio_duration=3.0, video_settings={"w": 1})
    h2 = scene_video_hash(scene, base_url="http://x", audio_duration=3.0, video_settings={"w": 1})
    assert h1 == h2
