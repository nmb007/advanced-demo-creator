from demo_creator.video.cursor_overlay import css_to_frame, sample_cursor_css


def test_sample_cursor_moves_into_target():
    timeline = {
        "width": 1920,
        "height": 1080,
        "cursor_paths": [
            {"t_start": 1.0, "t_end": 1.01, "x": 200.0, "y": 300.0},
        ],
    }
    # Before move: around center
    x0, y0 = sample_cursor_css(timeline, 0.2)
    assert abs(x0 - 960) < 1 and abs(y0 - 540) < 1
    # Mid synthetic move
    x1, y1 = sample_cursor_css(timeline, 0.85)
    assert x1 < 960
    assert y1 < 540
    # After: on target
    x2, y2 = sample_cursor_css(timeline, 1.5)
    assert abs(x2 - 200) < 1 and abs(y2 - 300) < 1


def test_css_to_frame_identity_at_zoom_1():
    ox, oy = css_to_frame(
        100,
        200,
        cam_cx=960,
        cam_cy=540,
        zoom=1.0,
        out_w=1920,
        out_h=1080,
        css_w=1920,
        css_h=1080,
    )
    assert abs(ox - 100) <= 1
    assert abs(oy - 200) <= 1
