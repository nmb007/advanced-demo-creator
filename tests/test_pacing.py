from demo_creator.plan.schema import Scene, Step, Target
from demo_creator.recorder.pacing import compute_delays, step_start_times


def _scene(n: int, pace: str = "spread", hold_after: float = 0.5) -> Scene:
    steps = [
        Step(action="click", target=Target(testid=f"b{i}"))
        for i in range(n)
    ]
    return Scene(id="s", narration="x", steps=steps, pace=pace, hold_after=hold_after)  # type: ignore[arg-type]


def test_spread_delays_sum_spare():
    scene = _scene(4, "spread")
    delays = compute_delays(scene, audio_duration=20.0, lead_in=0.3)
    assert len(delays) == 4
    # First step starts at lead_in → zero pre-delay after lead-in wait
    assert delays[0] == 0.0
    assert all(d >= 0.0 for d in delays)
    # Dense scenes must still get real gaps (not ~50ms) across long narration
    assert sum(delays) > 10.0


def test_spread_dense_scene_spaces_starts_across_audio():
    """Regression: many steps + long VO must not collapse to ~0.05s gaps."""
    scene = _scene(16, "spread", hold_after=1.5)
    audio = 21.0
    lead_in = 0.3
    starts = step_start_times(scene, audio, lead_in=lead_in)
    assert len(starts) == 16
    gaps = [starts[i + 1] - starts[i] for i in range(15)]
    assert min(gaps) > 0.5
    assert starts[0] == lead_in
    available = audio - lead_in - scene.hold_after
    assert starts[-1] == lead_in + (15 / 16) * available


def test_front_is_short():
    scene = _scene(3, "front")
    delays = compute_delays(scene, audio_duration=15.0)
    assert max(delays) <= 0.1
