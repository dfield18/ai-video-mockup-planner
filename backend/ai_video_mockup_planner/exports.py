"""
Export functionality for plans, shots, and storyboards.
Supports JSON and CSV formats.
"""
import json
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from .schemas import PlanAsset, ShotPlanAsset, ImageAsset, AssetStatus
from .storage import repository


def export_plan_json(project_id: str, plan_asset_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Export plan as JSON.

    Args:
        project_id: Project ID
        plan_asset_id: Plan asset ID (if None, use active)

    Returns:
        Plan JSON dict
    """
    project = repository.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    if plan_asset_id is None:
        plan_asset_id = project.active_plan_asset_id

    if not plan_asset_id:
        raise ValueError("No plan asset specified and no active plan found")

    plan_id, plan_version = _parse_asset_ref(plan_asset_id)
    plan = repository.get_plan_asset(project_id, plan_id, plan_version)

    if not plan:
        raise ValueError(f"Plan {plan_asset_id} not found")

    return plan.model_dump()


def export_characters_csv(project_id: str, plan_asset_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Export characters as CSV-ready list of dicts.

    Returns:
        List of character dicts
    """
    plan_json = export_plan_json(project_id, plan_asset_id)
    characters = plan_json.get("characters", [])

    # Flatten for CSV
    rows = []
    for char in characters:
        row = {
            "character_id": char.get("character_id"),
            "name": char.get("name"),
            "description": char.get("description"),
            "identity_lock": char.get("identity_lock"),
            "wardrobe_lock": char.get("wardrobe_lock"),
            "role": char.get("role"),
            "key_props": ", ".join(char.get("key_props", []))
        }
        rows.append(row)

    return rows


def export_shots_csv(project_id: str, shot_plan_asset_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Export shots as CSV-ready list of dicts.

    Returns:
        List of shot dicts
    """
    project = repository.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    if shot_plan_asset_id is None:
        shot_plan_asset_id = project.active_shot_plan_asset_id

    if not shot_plan_asset_id:
        raise ValueError("No shot plan asset specified and no active shot plan found")

    shot_plan_id, shot_plan_version = _parse_asset_ref(shot_plan_asset_id)
    shot_plan = repository.get_shot_plan_asset(project_id, shot_plan_id, shot_plan_version)

    if not shot_plan:
        raise ValueError(f"Shot plan {shot_plan_asset_id} not found")

    # Flatten for CSV
    rows = []
    for shot in shot_plan.shots:
        row = {
            "shot_id": shot.shot_id,
            "scene_id": shot.scene_id,
            "shot_index_in_scene": shot.shot_index_in_scene,
            "duration_s": shot.duration_s,
            "location_id": shot.location_id,
            "characters": ", ".join(shot.characters),
            "shot_type": shot.shot_type,
            "camera_angle": shot.camera.angle,
            "camera_movement": shot.camera.movement,
            "action_beats": " | ".join(shot.action_beats),
            "dialogue": shot.dialogue or "",
            "continuity_lock": shot.continuity_lock,
        }
        rows.append(row)

    return rows


def export_storyboard(
    project_id: str,
    include_images: bool = True,
    format: str = "json"
) -> Dict[str, Any]:
    """
    Export complete storyboard combining plan, shots, and images.

    Args:
        project_id: Project ID
        include_images: Whether to include image assets
        format: "json" or "csv"

    Returns:
        Storyboard data (format depends on format parameter)
    """
    project = repository.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Get active assets
    plan = None
    shot_plan = None

    if project.active_plan_asset_id:
        plan_id, plan_version = _parse_asset_ref(project.active_plan_asset_id)
        plan = repository.get_plan_asset(project_id, plan_id, plan_version)

    if project.active_shot_plan_asset_id:
        shot_plan_id, shot_plan_version = _parse_asset_ref(project.active_shot_plan_asset_id)
        shot_plan = repository.get_shot_plan_asset(project_id, shot_plan_id, shot_plan_version)

    storyboard = {
        "project": project.model_dump(),
        "plan": plan.model_dump() if plan else None,
        "shot_plan": shot_plan.model_dump() if shot_plan else None,
        "images": []
    }

    if include_images:
        # Get all accepted images, or all draft if none accepted
        images = repository.list_image_assets(project_id)
        accepted = [img for img in images if img.status == AssetStatus.ACCEPTED]
        if not accepted:
            # Use latest version of each image
            latest_images = _get_latest_images(images)
            storyboard["images"] = [img.model_dump() for img in latest_images]
        else:
            storyboard["images"] = [img.model_dump() for img in accepted]

    if format == "csv":
        # Return CSV-friendly structure
        return {
            "project": [project.model_dump()],
            "characters": export_characters_csv(project_id) if plan else [],
            "shots": export_shots_csv(project_id) if shot_plan else [],
            "images": [_flatten_image(img) for img in storyboard["images"]]
        }

    return storyboard


def _get_latest_images(images: List[ImageAsset]) -> List[ImageAsset]:
    """Get latest version of each unique image_id."""
    by_id: Dict[str, ImageAsset] = {}

    for img in images:
        if img.image_id not in by_id or img.version > by_id[img.image_id].version:
            by_id[img.image_id] = img

    return list(by_id.values())


def _flatten_image(image_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten image dict for CSV export."""
    return {
        "image_id": image_dict.get("image_id"),
        "version": image_dict.get("version"),
        "asset_type": image_dict.get("asset_type"),
        "shot_id": image_dict.get("shot_id"),
        "image_url": image_dict.get("image_url"),
        "status": image_dict.get("status"),
        "prompt_used": image_dict.get("prompt_used", "")[:200],  # Truncate
    }


def _parse_asset_ref(asset_ref: str) -> tuple[str, int]:
    """Parse asset reference into (stable_id, version)."""
    if '_v' in asset_ref:
        parts = asset_ref.rsplit('_v', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], int(parts[1])
    return asset_ref, 1
