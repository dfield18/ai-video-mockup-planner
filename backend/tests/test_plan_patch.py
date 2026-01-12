"""
Test plan patching creates new versions.
"""
from ai_video_mockup_planner.schemas import (
    PlanAsset, ProjectBible, Character
)
from ai_video_mockup_planner.plan_editing import (
    apply_patches, update_character, update_project_bible
)


def test_apply_character_patch():
    """Test patching a character field creates new version."""
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
                identity_lock="25 year old woman, brown hair",
                wardrobe_lock="Blue dress",
                role="protagonist"
            )
        ]
    )

    # Apply patch to make character older
    patches = [
        {
            "path": "characters[CHAR_01].identity_lock",
            "op": "replace",
            "value": "45 year old woman, gray hair"
        },
        {
            "path": "characters[CHAR_01].wardrobe_lock",
            "op": "replace",
            "value": "Black suit"
        }
    ]

    patched_plan = apply_patches(plan, patches)

    # Verify original is unchanged
    assert plan.characters[0].identity_lock == "25 year old woman, brown hair"
    assert plan.characters[0].wardrobe_lock == "Blue dress"

    # Verify patched has changes
    assert patched_plan.characters[0].identity_lock == "45 year old woman, gray hair"
    assert patched_plan.characters[0].wardrobe_lock == "Black suit"


def test_update_character_convenience():
    """Test convenience function for updating character."""
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
                name="Bob",
                description="Antagonist",
                identity_lock="30 year old man, bald",
                role="antagonist"
            )
        ]
    )

    updated_plan = update_character(plan, "CHAR_01", {
        "description": "Anti-hero",
        "role": "anti-hero"
    })

    # Verify original unchanged
    assert plan.characters[0].description == "Antagonist"
    assert plan.characters[0].role == "antagonist"

    # Verify updated has changes
    assert updated_plan.characters[0].description == "Anti-hero"
    assert updated_plan.characters[0].role == "anti-hero"
    # Unchanged fields remain
    assert updated_plan.characters[0].identity_lock == "30 year old man, bald"


def test_update_project_bible():
    """Test updating project bible fields."""
    plan = PlanAsset(
        plan_id="plan_1",
        version=1,
        source_script_id="script_1",
        source_script_version=1,
        project_id="proj_1",
        project_bible=ProjectBible(
            title="Original Title",
            genre="Drama",
            tone="Serious",
            style="cinematic",
            aspect_ratio="16:9",
            target_duration_s=30,
            visual_realism="high",
            pacing="medium"
        )
    )

    updated_plan = update_project_bible(plan, {
        "title": "New Title",
        "pacing": "fast"
    })

    # Verify original unchanged
    assert plan.project_bible.title == "Original Title"
    assert plan.project_bible.pacing == "medium"

    # Verify updated has changes
    assert updated_plan.project_bible.title == "New Title"
    assert updated_plan.project_bible.pacing == "fast"
    # Unchanged fields remain
    assert updated_plan.project_bible.genre == "Drama"
