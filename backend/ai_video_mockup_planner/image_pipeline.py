"""
Image generation and editing pipeline.
Uses stubs for MVP but implements full prompt construction and versioning logic.
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from .schemas import (
    PlanAsset, ShotPlanAsset, ImageAsset, ImageAssetType, LockProfile,
    RegenScope, RegenScopeType, AssetStatus
)
from .storage import repository
from .prompt_builders import (
    build_style_frame_prompt,
    build_character_reference_prompt,
    build_location_reference_prompt,
    build_shot_frame_prompt,
    build_image_edit_prompt,
    build_regenerate_prompt
)
from .gemini_client import get_gemini_client
from .prompts import INTERPRET_IMAGE_FEEDBACK_PROMPT_V1
from .config import config
from .utils import generate_id


# ────────────────────────────────────────────────────────────────────────────────
# IMAGE GENERATION
# ────────────────────────────────────────────────────────────────────────────────

def generate_images(
    project_id: str,
    scope: RegenScope,
    lock_profile: Optional[LockProfile] = None
) -> List[ImageAsset]:
    """
    Generate images for a given scope.

    Args:
        project_id: Project ID
        scope: What to generate images for
        lock_profile: Optional lock profile for regeneration

    Returns:
        List of created ImageAsset objects
    """
    project = repository.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Get active plan and shot plan
    plan = None
    shot_plan = None

    if project.active_plan_asset_id:
        plan_id, plan_version = _parse_asset_ref(project.active_plan_asset_id)
        plan = repository.get_plan_asset(project_id, plan_id, plan_version)

    if project.active_shot_plan_asset_id:
        shot_plan_id, shot_plan_version = _parse_asset_ref(project.active_shot_plan_asset_id)
        shot_plan = repository.get_shot_plan_asset(project_id, shot_plan_id, shot_plan_version)

    if not plan:
        raise ValueError("No active plan found")

    images: List[ImageAsset] = []

    if scope.scope_type == RegenScopeType.PROJECT:
        # Generate all images for project
        images.extend(_generate_style_frame(project_id, plan))
        images.extend(_generate_character_references(project_id, plan))
        images.extend(_generate_location_references(project_id, plan))
        if shot_plan:
            images.extend(_generate_shot_frames(project_id, plan, shot_plan, lock_profile))

    elif scope.scope_type == RegenScopeType.SCENE:
        # Generate shot frames for a specific scene
        if not shot_plan:
            raise ValueError("No active shot plan found")
        scene_shots = [shot for shot in shot_plan.shots if shot.scene_id == scope.scene_id]
        for shot in scene_shots:
            img = _generate_shot_frame(project_id, plan, shot, lock_profile)
            images.append(img)

    elif scope.scope_type == RegenScopeType.SHOT:
        # Generate shot frame for a specific shot
        if not shot_plan:
            raise ValueError("No active shot plan found")
        shot = next((s for s in shot_plan.shots if s.shot_id == scope.shot_id), None)
        if not shot:
            raise ValueError(f"Shot {scope.shot_id} not found")
        img = _generate_shot_frame(project_id, plan, shot, lock_profile)
        images.append(img)

    elif scope.scope_type == RegenScopeType.ASSET:
        # Regenerate specific asset type
        if scope.asset_type == ImageAssetType.STYLE_FRAME:
            images.extend(_generate_style_frame(project_id, plan))
        elif scope.asset_type == ImageAssetType.CHARACTER_REFERENCE:
            images.extend(_generate_character_references(project_id, plan))
        elif scope.asset_type == ImageAssetType.LOCATION_REFERENCE:
            images.extend(_generate_location_references(project_id, plan))

    return images


def _generate_style_frame(project_id: str, plan: PlanAsset) -> List[ImageAsset]:
    """Generate style frame image."""
    prompt, negative_prompt = build_style_frame_prompt(plan, project_id)

    # Stub: create placeholder image
    image_url = f"placeholder://style_frame_{generate_id()}.jpg"

    image = ImageAsset(
        image_id=generate_id("img_style_"),
        version=1,
        asset_type=ImageAssetType.STYLE_FRAME,
        project_id=project_id,
        plan_id=plan.plan_id,
        image_url=image_url,
        prompt_used=prompt,
        negative_prompt=negative_prompt,
        status=AssetStatus.DRAFT
    )

    repository.create_image_asset(image)
    return [image]


def _generate_character_references(project_id: str, plan: PlanAsset) -> List[ImageAsset]:
    """Generate character reference images."""
    images = []

    for character in plan.characters:
        prompt, negative_prompt = build_character_reference_prompt(character, plan, project_id)

        # Stub: create placeholder image
        image_url = f"placeholder://character_{character.character_id}_{generate_id()}.jpg"

        image = ImageAsset(
            image_id=generate_id(f"img_char_{character.character_id}_"),
            version=1,
            asset_type=ImageAssetType.CHARACTER_REFERENCE,
            project_id=project_id,
            plan_id=plan.plan_id,
            character_ids=[character.character_id],
            image_url=image_url,
            prompt_used=prompt,
            negative_prompt=negative_prompt,
            status=AssetStatus.DRAFT
        )

        repository.create_image_asset(image)
        images.append(image)

    return images


def _generate_location_references(project_id: str, plan: PlanAsset) -> List[ImageAsset]:
    """Generate location reference images."""
    images = []

    for location in plan.locations:
        prompt, negative_prompt = build_location_reference_prompt(location, plan, project_id)

        # Stub: create placeholder image
        image_url = f"placeholder://location_{location.location_id}_{generate_id()}.jpg"

        image = ImageAsset(
            image_id=generate_id(f"img_loc_{location.location_id}_"),
            version=1,
            asset_type=ImageAssetType.LOCATION_REFERENCE,
            project_id=project_id,
            plan_id=plan.plan_id,
            location_id=location.location_id,
            image_url=image_url,
            prompt_used=prompt,
            negative_prompt=negative_prompt,
            status=AssetStatus.DRAFT
        )

        repository.create_image_asset(image)
        images.append(image)

    return images


def _generate_shot_frames(
    project_id: str,
    plan: PlanAsset,
    shot_plan: ShotPlanAsset,
    lock_profile: Optional[LockProfile] = None
) -> List[ImageAsset]:
    """Generate shot frame images for all shots."""
    images = []

    for shot in shot_plan.shots:
        img = _generate_shot_frame(project_id, plan, shot, lock_profile)
        images.append(img)

    return images


def _generate_shot_frame(
    project_id: str,
    plan: PlanAsset,
    shot,
    lock_profile: Optional[LockProfile] = None
) -> ImageAsset:
    """Generate a single shot frame image."""
    prompt, negative_prompt = build_shot_frame_prompt(shot, plan, lock_profile, project_id)

    # Stub: create placeholder image
    image_url = f"placeholder://shot_{shot.shot_id}_{generate_id()}.jpg"

    if lock_profile is None:
        lock_profile = LockProfile()

    image = ImageAsset(
        image_id=generate_id(f"img_shot_{shot.shot_id}_"),
        version=1,
        asset_type=ImageAssetType.SHOT_FRAME,
        project_id=project_id,
        plan_id=plan.plan_id,
        shot_id=shot.shot_id,
        character_ids=shot.characters,
        location_id=shot.location_id,
        image_url=image_url,
        prompt_used=prompt,
        negative_prompt=negative_prompt,
        lock_profile=lock_profile,
        status=AssetStatus.DRAFT
    )

    repository.create_image_asset(image)
    return image


# ────────────────────────────────────────────────────────────────────────────────
# IMAGE ACTIONS
# ────────────────────────────────────────────────────────────────────────────────

def accept_image(project_id: str, image_asset_id: str) -> ImageAsset:
    """
    Accept an image (mark as accepted).
    Does not create new version, just updates status.
    """
    image_id, version = _parse_asset_ref(image_asset_id)
    image = repository.get_image_asset(project_id, image_id, version)

    if not image:
        raise ValueError(f"Image {image_asset_id} not found")

    image.status = AssetStatus.ACCEPTED
    repository.create_image_asset(image)  # Overwrite with updated status
    return image


def edit_image(
    project_id: str,
    image_asset_id: str,
    feedback: str,
    lock_profile: Optional[LockProfile] = None
) -> ImageAsset:
    """
    Edit an image based on user feedback.
    Interprets feedback, builds new prompt, creates new version.
    """
    image_id, version = _parse_asset_ref(image_asset_id)
    parent_image = repository.get_image_asset(project_id, image_id, version)

    if not parent_image:
        raise ValueError(f"Image {image_asset_id} not found")

    # Interpret feedback using LLM
    client = get_gemini_client()
    prompt = INTERPRET_IMAGE_FEEDBACK_PROMPT_V1.format(
        image_asset_json=json.dumps(parent_image.model_dump(), indent=2, default=str),
        user_feedback=feedback
    )

    result = client.generate_json(
        prompt=prompt,
        prompt_version=config.INTERPRET_IMAGE_FEEDBACK_PROMPT_VERSION,
        project_id=project_id
    )

    edit_delta = result.get("edit_delta", {})

    # Build new prompt
    if lock_profile is None:
        lock_profile = parent_image.lock_profile

    new_prompt = build_image_edit_prompt(
        parent_image.prompt_used,
        edit_delta,
        lock_profile
    )

    # Build new negative prompt (add removed elements)
    new_negative = parent_image.negative_prompt
    remove_elements = edit_delta.get("remove_elements", [])
    if remove_elements:
        new_negative += ", " + ", ".join(remove_elements)

    # Stub: create placeholder image
    image_url = f"placeholder://edited_{image_id}_v{version + 1}_{generate_id()}.jpg"

    # Create new version
    new_image = ImageAsset(
        image_id=image_id,  # Same stable ID
        version=version + 1,
        asset_type=parent_image.asset_type,
        project_id=project_id,
        plan_id=parent_image.plan_id,
        shot_plan_id=parent_image.shot_plan_id,
        shot_id=parent_image.shot_id,
        character_ids=parent_image.character_ids,
        location_id=parent_image.location_id,
        image_url=image_url,
        prompt_used=new_prompt,
        negative_prompt=new_negative,
        lock_profile=lock_profile,
        status=AssetStatus.DRAFT,
        parent_image_asset_id=image_asset_id
    )

    repository.create_image_asset(new_image)
    return new_image


def regenerate_image(
    project_id: str,
    image_asset_id: str,
    lock_profile: Optional[LockProfile] = None
) -> ImageAsset:
    """
    Regenerate an image with lock profile constraints.
    Creates new version with same prompt but emphasizing locks.
    """
    image_id, version = _parse_asset_ref(image_asset_id)
    parent_image = repository.get_image_asset(project_id, image_id, version)

    if not parent_image:
        raise ValueError(f"Image {image_asset_id} not found")

    # Build regenerate prompt
    if lock_profile is None:
        lock_profile = parent_image.lock_profile

    new_prompt = build_regenerate_prompt(
        parent_image.prompt_used,
        lock_profile
    )

    # Build new negative prompt with banned elements
    new_negative = parent_image.negative_prompt
    if lock_profile.banned_elements:
        new_negative += ", " + ", ".join(lock_profile.banned_elements)

    # Stub: create placeholder image
    image_url = f"placeholder://regen_{image_id}_v{version + 1}_{generate_id()}.jpg"

    # Create new version
    new_image = ImageAsset(
        image_id=image_id,
        version=version + 1,
        asset_type=parent_image.asset_type,
        project_id=project_id,
        plan_id=parent_image.plan_id,
        shot_plan_id=parent_image.shot_plan_id,
        shot_id=parent_image.shot_id,
        character_ids=parent_image.character_ids,
        location_id=parent_image.location_id,
        image_url=image_url,
        prompt_used=new_prompt,
        negative_prompt=new_negative,
        lock_profile=lock_profile,
        status=AssetStatus.DRAFT,
        parent_image_asset_id=image_asset_id
    )

    repository.create_image_asset(new_image)
    return new_image


# ────────────────────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────────────────────

def _parse_asset_ref(asset_ref: str) -> tuple[str, int]:
    """Parse asset reference into (stable_id, version)."""
    if '_v' in asset_ref:
        parts = asset_ref.rsplit('_v', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], int(parts[1])
    return asset_ref, 1
