from demo_creator.plan.schema import Scene, Step, Target
from demo_creator.recorder.pacing import compute_delays


def _scene(n: int, pace: str = "spread") -> Scene:
    steps = [
        Step(action="click", target=Target(testid=f"b{i}"))
        for i in range(n)
    ]
    return Scene(id="s", narration="x", steps=steps, pace=pace)  # type: ignore[arg-type]


def test_spread_delays_sum_spare():
    scene = _scene(4, "spread")
    delays = compute_delays(scene, audio_duration=20.0, lead_in=0.3)
    assert len(delays) == 4
    assert all(d >= 0.05 for d in delays)


def test_front_is_short():
    scene = _scene(3, "front")
    delays = compute_delays(scene, audio_duration=15.0)
    assert max(delays) <= 0.1
