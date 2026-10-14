from demo_creator.video.zoom import build_camera_track, sample_camera


def test_camera_track_merges_nearby_actions():
    timeline = {
        "duration": 10.0,
        "steps": [
            {
                "t_start": 1.0,
                "t_end": 1.2,
                "zoom": 1.5,
                "box": {"x": 100, "y": 100, "width": 40, "height": 20},
            },
            {
                "t_start": 1.5,
                "t_end": 1.7,
                "zoom": 1.5,
                "box": {"x": 120, "y": 110, "width": 40, "height": 20},
            },
            {
                "t_start": 6.0,
                "t_end": 6.2,
                "zoom": 1.6,
                "box": {"x": 800, "y": 500, "width": 50, "height": 30},
            },
        ],
    }
    track = build_camera_track(timeline)
    assert len(track) >= 3
    cx, cy, z = sample_camera(track, 1.1)
    assert z >= 1.0
    assert 0 < cx < 1920


def test_zoom_capped():
    timeline = {
        "duration": 3.0,
        "steps": [
            {
                "t_start": 1.0,
                "t_end": 1.1,
                "zoom": 5.0,
                "box": {"x": 10, "y": 10, "width": 5, "height": 5},
            }
        ],
    }
    track = build_camera_track(timeline)
    _, _, z = sample_camera(track, 1.0)
    assert z <= 2.0
