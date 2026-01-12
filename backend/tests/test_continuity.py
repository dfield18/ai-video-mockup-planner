"""
Test continuity validators catch issues.
"""
from ai_video_mockup_planner.schemas import (
    PlanAsset, ShotPlanAsset, Shot, ProjectBible, Character, Location,
    CameraSetup, StateDict
)
from ai_video_mockup_planner.continuity import (
    validate_shot_plan,
    _validate_missing_entities,
    _validate_state_continuity,
    _validate_required_fields
)


def test_missing_entity_detection():
    """Test that validator catches missing entity references."""
    plan = PlanAsset(
        plan_id="plan_1",
        version=1,
        source_script_id="script_1",
        source_script_version=1,
        project_id="proj_1",
        project_bible=ProjectBible(
            title="Test",
            genre="Drama",
            tone="Serious",
            style="cinematic",
            aspect_ratio="16:9",
            target_duration_s=30,
            visual_realism="high",
            pacing="medium"
        ),
        characters=[
            Character(
                character_id="CHAR_01",
                name="Alice",
                description="Protagonist",
                identity_lock="Woman, 30s",
                role="protagonist"
            )
        ],
        locations=[
            Location(
                location_id="LOC_01",
                name="Office",
                description="Modern office",
                location_lock="Glass walls, desk"
            )
        ]
    )

    # Shot references non-existent character
    shot_plan = ShotPlanAsset(
        shot_plan_id="shotplan_1",
        version=1,
        project_id="proj_1",
        plan_id="plan_1",
        plan_version=1,
        shots=[
            Shot(
                shot_id="S001",
                scene_id="SC001",
                shot_index_in_scene=0,
                duration_s=5.0,
                location_id="LOC_01",
                characters=["CHAR_99"],  # Non-existent!
                shot_type="medium",
                camera=CameraSetup(shot_type="medium"),
                continuity_lock="Character wears blue",
                state_in=StateDict(),
                state_out=StateDict()
            )
        ]
    )

    issues = _validate_missing_entities(plan, shot_plan)

    # Should have at least 2 errors: missing scene and missing character
    assert len(issues) >= 2
    error_messages = [issue.message for issue in issues]
    assert any("CHAR_99" in msg for msg in error_messages)
    assert any("SC001" in msg for msg in error_messages)


def test_state_conflict_detection():
    """Test that validator catches state conflicts within scenes."""
    plan = PlanAsset(
        plan_id="plan_1",
        version=1,
        source_script_id="script_1",
        source_script_version=1,
        project_id="proj_1",
        project_bible=ProjectBible(
            title="Test",
            genre="Drama",
            tone="Serious",
            style="cinematic",
            aspect_ratio="16:9",
            target_duration_s=30,
            visual_realism="high",
            pacing="medium"
        )
    )

    # Two shots in same scene with conflicting time_of_day
    shot_plan = ShotPlanAsset(
        shot_plan_id="shotplan_1",
        version=1,
        project_id="proj_1",
        plan_id="plan_1",
        plan_version=1,
        shots=[
            Shot(
                shot_id="S001",
                scene_id="SC001",
                shot_index_in_scene=0,
                duration_s=3.0,
                location_id="LOC_01",
                characters=[],
                shot_type="wide",
                camera=CameraSetup(shot_type="wide"),
                continuity_lock="Daytime",
                state_in=StateDict(time_of_day="morning"),
                state_out=StateDict(time_of_day="morning")
            ),
            Shot(
                shot_id="S002",
                scene_id="SC001",
                shot_index_in_scene=1,
                duration_s=3.0,
                location_id="LOC_01",
                characters=[],
                shot_type="medium",
                camera=CameraSetup(shot_type="medium"),
                continuity_lock="Nighttime",
                state_in=StateDict(time_of_day="night"),  # Conflict!
                state_out=StateDict(time_of_day="night")
            )
        ]
    )

    issues = _validate_state_continuity(shot_plan)

    # Should detect time_of_day conflict
    assert len(issues) > 0, f"Expected issues but got none"
    # Check if any issue is about time_of_day
    has_time_issue = any("time" in issue.message.lower() for issue in issues)
    if not has_time_issue:
        print(f"Issues found: {[issue.message for issue in issues]}")
    assert has_time_issue, f"Expected time_of_day issue but got: {[issue.message for issue in issues]}"


def test_missing_required_fields():
    """Test that validator catches missing continuity_lock."""
    plan = PlanAsset(
        plan_id="plan_1",
        version=1,
        source_script_id="script_1",
        source_script_version=1,
        project_id="proj_1",
        project_bible=ProjectBible(
            title="Test",
            genre="Drama",
            tone="Serious",
            style="cinematic",
            aspect_ratio="16:9",
            target_duration_s=30,
            visual_realism="high",
            pacing="medium"
        )
    )

    # Shot missing continuity_lock
    shot_plan = ShotPlanAsset(
        shot_plan_id="shotplan_1",
        version=1,
        project_id="proj_1",
        plan_id="plan_1",
        plan_version=1,
        shots=[
            Shot(
                shot_id="S001",
                scene_id="SC001",
                shot_index_in_scene=0,
                duration_s=5.0,
                location_id="LOC_01",
                characters=[],
                shot_type="wide",
                camera=CameraSetup(shot_type="wide"),
                continuity_lock="",  # Empty!
                state_in=StateDict(),
                state_out=StateDict()
            )
        ]
    )

    issues = _validate_required_fields(shot_plan)

    # Should detect missing continuity_lock
    assert len(issues) > 0
    assert any("continuity_lock" in issue.message.lower() for issue in issues)
