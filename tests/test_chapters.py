from demo_creator.video.chapters import format_ffmetadata


def test_ffmetadata_chapters():
    text = format_ffmetadata([("Intro", 0.0, 5.0), ("Main", 5.0, 12.5)])
    assert ";FFMETADATA1" in text
    assert "title=Intro" in text
    assert "START=0" in text
    assert "START=5000" in text
    assert "END=12500" in text
