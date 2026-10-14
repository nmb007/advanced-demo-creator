"""Compute inter-step delays to pace actions to narration duration."""

from __future__ import annotations

from demo_creator.plan.schema import PaceMode, Scene


def compute_delays(
    scene: Scene,
    audio_duration: float,
    *,
    lead_in: float = 0.3,
    base_action_estimate: float = 1.2,
) -> list[float]:
    """
    Return a delay (seconds) to sleep BEFORE each step, after lead-in.
    Length equals len(scene.steps).
    """
    n = len(scene.steps)
    if n == 0:
        return []

    available = max(0.0, audio_duration - lead_in - scene.hold_after)
    estimated_actions = n * base_action_estimate
    spare = max(0.0, available - estimated_actions)

    if scene.pace == "front":
        # Front-load actions: small delays early, dump spare at end (handled by hold)
        return [0.05] * n
    if scene.pace == "back":
        # Wait most of the spare first, then act
        delays = [0.05] * n
        delays[0] = spare * 0.8
        return delays

    # spread
    per = spare / n if n else 0.0
    return [0.05 + per for _ in range(n)]
