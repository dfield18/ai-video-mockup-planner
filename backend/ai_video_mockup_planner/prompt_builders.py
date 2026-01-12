"""
Prompt building functions for image generation.
Deterministic construction of prompts based on plan metadata.
"""
import json
from typing import Dict, Any, List, Optional

from .schemas import (
    PlanAsset, Shot, Character, Location, LockProfile, ImageAssetType
)
from .gemini_client import get_gemini_client
from .prompts import (
    BUILD_STYLE_FRAME_PROMPT_V1,
    BUILD_CHARACTER_REFERENCE_PROMPT_V1,
    BUILD_LOCATION_REFERENCE_PROMPT_V1,
    BUILD_SHOT_FRAME_PROMPT_V1
)
from .config import config


def build_style_frame_prompt(
    plan: PlanAsset,
    project_id: str
) -> tuple[str, str]:
    """
    Build style frame prompt using LLM.

    Returns:
        (prompt, negative_prompt)
    """
    client = get_gemini_client()

    llm_prompt = BUILD_STYLE_FRAME_PROMPT_V1.format(
        project_bible_json=json.dumps(plan.project_bible.model_dump(), indent=2)
    )

    result = client.generate_json(
        prompt=llm_prompt,
        prompt_version=config.BUILD_STYLE_FRAME_PROMPT_VERSION,
        project_id=project_id
    )

    return result.get("prompt", ""), result.get("negative_prompt", "")


def build_character_reference_prompt(
    character: Character,
    plan: PlanAsset,
    project_id: str
) -> tuple[str, str]:
    """
    Build character reference prompt using LLM.

    Returns:
        (prompt, negative_prompt)
    """
    client = get_gemini_client()

    style_description = f"{plan.project_bible.style}, {plan.project_bible.tone}, {plan.project_bible.visual_realism} realism"

    llm_prompt = BUILD_CHARACTER_REFERENCE_PROMPT_V1.format(
        character_json=json.dumps(character.model_dump(), indent=2),
        style_description=style_description
    )

    result = client.generate_json(
        prompt=llm_prompt,
        prompt_version=config.BUILD_CHARACTER_REFERENCE_PROMPT_VERSION,
        project_id=project_id
    )

    return result.get("prompt", ""), result.get("negative_prompt", "")


def build_location_reference_prompt(
    location: Location,
    plan: PlanAsset,
    project_id: str
) -> tuple[str, str]:
    """
    Build location reference prompt using LLM.

    Returns:
        (prompt, negative_prompt)
    """
    client = get_gemini_client()

    style_description = f"{plan.project_bible.style}, {plan.project_bible.tone}, {plan.project_bible.visual_realism} realism"

    llm_prompt = BUILD_LOCATION_REFERENCE_PROMPT_V1.format(
        location_json=json.dumps(location.model_dump(), indent=2),
        style_description=style_description
    )

    result = client.generate_json(
        prompt=llm_prompt,
        prompt_version=config.BUILD_LOCATION_REFERENCE_PROMPT_VERSION,
        project_id=project_id
    )

    return result.get("prompt", ""), result.get("negative_prompt", "")


def build_shot_frame_prompt(
    shot: Shot,
    plan: PlanAsset,
    lock_profile: Optional[LockProfile] = None,
    project_id: str = ""
) -> tuple[str, str]:
    """
    Build shot frame prompt using LLM.

    Returns:
        (prompt, negative_prompt)
    """
    client = get_gemini_client()

    # Get characters in shot
    characters = [char for char in plan.characters if char.character_id in shot.characters]

    # Get location
    location = next((loc for loc in plan.locations if loc.location_id == shot.location_id), None)

    # Default lock profile
    if lock_profile is None:
        lock_profile = LockProfile()

    style_description = f"{plan.project_bible.style}, {plan.project_bible.tone}, {plan.project_bible.visual_realism} realism"

    llm_prompt = BUILD_SHOT_FRAME_PROMPT_V1.format(
        shot_json=json.dumps(shot.model_dump(), indent=2, default=str),
        characters_json=json.dumps([char.model_dump() for char in characters], indent=2),
        location_json=json.dumps(location.model_dump(), indent=2) if location else "{}",
        style_description=style_description,
        lock_profile_json=json.dumps(lock_profile.model_dump(), indent=2)
    )

    result = client.generate_json(
        prompt=llm_prompt,
        prompt_version=config.BUILD_SHOT_FRAME_PROMPT_VERSION,
        project_id=project_id
    )

    return result.get("prompt", ""), result.get("negative_prompt", "")


def build_image_edit_prompt(
    original_prompt: str,
    edit_delta: Dict[str, Any],
    lock_profile: LockProfile
) -> str:
    """
    Build edited prompt by applying edit delta to original prompt.
    Deterministic composition.

    Args:
        original_prompt: The original prompt
        edit_delta: Structured edits from interpret_image_feedback
        lock_profile: What to preserve

    Returns:
        New prompt with edits applied
    """
    # Start with base prompt
    new_prompt = original_prompt

    # Add elements
    add_elements = edit_delta.get("add_elements", [])
    if add_elements:
        additions = ", ".join(add_elements)
        new_prompt += f". Add: {additions}"

    # Remove elements (add to negative prompt instead)
    # Style adjustments
    style_adjustments = edit_delta.get("style_adjustments", [])
    if style_adjustments:
        adjustments = ", ".join(style_adjustments)
        new_prompt += f". Style: {adjustments}"

    # Camera adjustments
    camera_adjustments = edit_delta.get("camera_adjustments", {})
    if camera_adjustments.get("angle"):
        new_prompt += f". Camera angle: {camera_adjustments['angle']}"
    if camera_adjustments.get("distance"):
        new_prompt += f". Camera distance: {camera_adjustments['distance']}"

    # Updated guidance
    guidance = edit_delta.get("updated_prompt_guidance", "")
    if guidance:
        new_prompt += f". {guidance}"

    return new_prompt


def build_regenerate_prompt(
    original_prompt: str,
    lock_profile: LockProfile
) -> str:
    """
    Build regeneration prompt with lock profile constraints.

    Args:
        original_prompt: The original prompt
        lock_profile: What to preserve

    Returns:
        Prompt with lock constraints emphasized
    """
    constraints = []

    if lock_profile.preserve_identity:
        constraints.append("PRESERVE character identities exactly")
    if lock_profile.preserve_wardrobe:
        constraints.append("PRESERVE wardrobe exactly")
    if lock_profile.preserve_location_layout:
        constraints.append("PRESERVE location layout exactly")
    if lock_profile.preserve_time_of_day:
        constraints.append("PRESERVE time of day and lighting exactly")
    if lock_profile.preserve_camera:
        constraints.append("PRESERVE camera angle and framing exactly")
    if lock_profile.preserve_pose:
        constraints.append("PRESERVE character poses exactly")

    if lock_profile.must_keep_elements:
        must_keep = ", ".join(lock_profile.must_keep_elements)
        constraints.append(f"MUST KEEP: {must_keep}")

    constraint_text = ". ".join(constraints)

    return f"{original_prompt}. CONSTRAINTS: {constraint_text}"
