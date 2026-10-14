from pathlib import Path

import pytest

from demo_creator.plan.loader import expand_string, load_plan, validate_plan_summary
from demo_creator.plan.schema import DemoPlan, Step, Target


def test_target_requires_locator():
    with pytest.raises(Exception):
        Target()


def test_step_fill_requires_value():
    with pytest.raises(Exception):
        Step(action="fill", target=Target(label="User"))


def test_expand_env_and_unique():
    out = expand_string("hi ${DEMO_USER}-${UNIQUE}", {"DEMO_USER": "admin"}, "1014-1506")
    assert out == "hi admin-1014-1506"


def test_estimate_seconds():
    plan = DemoPlan(
        title="t",
        chapters=[
            {
                "title": "A",
                "scenes": [
                    {"id": "s1", "narration": "one two three four five", "steps": []},
                ],
            }
        ],
    )
    est = plan.estimate_seconds(words_per_minute=150)
    assert est["scene_count"] == 1
    assert est["total_seconds"] > 0


def test_load_fixture_plan(tmp_path: Path):
    src = Path(__file__).parent / "fixtures" / "plan.yaml"
    plan = load_plan(src, unique="0101-0000")
    assert plan.title.startswith("Fixture")
    assert len(plan.all_scenes()) == 2
    # UNIQUE expanded in course name step
    step = plan.chapters[1].scenes[0].steps[1]
    assert "0101-0000" in (step.value or "")


def test_validate_plan_summary():
    src = Path(__file__).parent / "fixtures" / "plan.yaml"
    summary = validate_plan_summary(src)
    assert summary["valid"] is True
    assert summary["estimate"]["chapter_count"] == 2
