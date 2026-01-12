"""
Main pipeline orchestration for AI Video Mockup Planner.
Coordinates planning, shot generation, and image creation.
"""
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from .schemas import (
    Project, ScriptAsset, PlanAsset, ShotPlanAsset, Shot,
    ProjectBible, Character, Location, PropWardrobe, Scene,
    Job, JobStatus, JobType, AssetStatus, Beat, CameraSetup, StateDict
)
from .storage import repository
from .gemini_client import get_gemini_client
from .prompts import EXTRACT_PLAN_PROMPT_V1, GENERATE_SHOTS_PROMPT_V1
from .continuity import validate_shot_plan, repair_shot_plan
from .plan_editing import apply_patches
from .config import config
from .utils import generate_id, build_asset_id


# ────────────────────────────────────────────────────────────────────────────────
# PROJECT MANAGEMENT
# ────────────────────────────────────────────────────────────────────────────────

def create_project(title: str, user_id: Optional[str] = None) -> Project:
    """Create a new project."""
    project = Project(
        project_id=generate_id("proj_"),
        title=title,
        user_id=user_id
    )
    return repository.create_project(project)


def get_project(project_id: str) -> Optional[Project]:
    """Get project by ID."""
    return repository.get_project(project_id)


# ────────────────────────────────────────────────────────────────────────────────
# SCRIPT MANAGEMENT
# ────────────────────────────────────────────────────────────────────────────────

def create_script(
    project_id: str,
    content: str,
    title: Optional[str] = None
) -> ScriptAsset:
    """Create a new script asset (version 1)."""
    project = repository.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    script = ScriptAsset(
        script_id=generate_id("script_"),
        version=1,
        content=content,
        title=title,
        project_id=project_id
    )

    repository.create_script_asset(script)

    # Update project active pointer
    project.active_script_asset_id = build_asset_id(script.script_id, script.version)
    repository.update_project(project)

    return script


def update_script(
    project_id: str,
    script_id: str,
    content: str,
    title: Optional[str] = None
) -> ScriptAsset:
    """Create new version of existing script."""
    # Get latest version
    existing = repository.get_script_asset(project_id, script_id)
    if not existing:
        raise ValueError(f"Script {script_id} not found")

    new_version = existing.version + 1
    parent_asset_id = build_asset_id(script_id, existing.version)

    script = ScriptAsset(
        script_id=script_id,
        version=new_version,
        content=content,
        title=title or existing.title,
        parent_script_asset_id=parent_asset_id,
        project_id=project_id
    )

    repository.create_script_asset(script)

    # Update project active pointer
    project = repository.get_project(project_id)
    project.active_script_asset_id = build_asset_id(script_id, new_version)
    repository.update_project(project)

    return script


# ────────────────────────────────────────────────────────────────────────────────
# PLAN GENERATION
# ────────────────────────────────────────────────────────────────────────────────

def generate_plan(
    project_id: str,
    script_asset_id: Optional[str] = None,
    preferences: Optional[Dict[str, Any]] = None
) -> PlanAsset:
    """
    Generate a plan from script using LLM.

    Args:
        project_id: Project ID
        script_asset_id: Script asset ID (if None, use active)
        preferences: User preferences for plan generation

    Returns:
        Created PlanAsset
    """
    # Create job
    job = Job(
        job_id=generate_id("job_"),
        project_id=project_id,
        job_type=JobType.EXTRACT_PLAN,
        status=JobStatus.RUNNING,
        started_at=datetime.utcnow()
    )
    repository.create_job(job)

    try:
        project = repository.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Get script
        if script_asset_id is None:
            script_asset_id = project.active_script_asset_id

        if not script_asset_id:
            raise ValueError("No script asset specified and no active script found")

        script_id, script_version = _parse_asset_ref(script_asset_id)
        script = repository.get_script_asset(project_id, script_id, script_version)

        if not script:
            raise ValueError(f"Script {script_asset_id} not found")

        # Merge preferences with defaults
        prefs = _merge_preferences(preferences)

        # Call LLM
        client = get_gemini_client()
        prompt = EXTRACT_PLAN_PROMPT_V1.format(
            script_content=script.content,
            preferences_json=json.dumps(prefs, indent=2)
        )

        result = client.generate_json(
            prompt=prompt,
            prompt_version=config.EXTRACT_PLAN_PROMPT_VERSION,
            project_id=project_id
        )

        # Parse result into PlanAsset
        plan = _parse_plan_result(result, project_id, script.script_id, script.version)

        repository.create_plan_asset(plan)

        # Update project active pointer
        project.active_plan_asset_id = build_asset_id(plan.plan_id, plan.version)
        repository.update_project(project)

        # Update job
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.progress = 1.0
        job.output_refs = {"plan_asset_id": build_asset_id(plan.plan_id, plan.version)}
        repository.update_job(job)

        return plan

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.utcnow()
        repository.update_job(job)
        raise


def patch_plan(
    project_id: str,
    plan_asset_id: Optional[str],
    patches: List[Dict[str, Any]]
) -> PlanAsset:
    """
    Apply patches to plan, creating new version.

    Args:
        project_id: Project ID
        plan_asset_id: Plan asset ID (if None, use active)
        patches: List of patch operations

    Returns:
        New PlanAsset with patches applied
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

    # Apply patches
    patched_plan = apply_patches(plan, patches)

    # Create new version
    new_version = plan.version + 1
    patched_plan.plan_id = plan_id
    patched_plan.version = new_version
    patched_plan.parent_plan_asset_id = build_asset_id(plan_id, plan_version)

    repository.create_plan_asset(patched_plan)

    # Update project active pointer
    project.active_plan_asset_id = build_asset_id(plan_id, new_version)
    repository.update_project(project)

    return patched_plan


# ────────────────────────────────────────────────────────────────────────────────
# SHOT GENERATION
# ────────────────────────────────────────────────────────────────────────────────

def generate_shots(
    project_id: str,
    plan_asset_id: Optional[str] = None
) -> ShotPlanAsset:
    """
    Generate shot plan from plan using LLM with continuity validation.

    Args:
        project_id: Project ID
        plan_asset_id: Plan asset ID (if None, use active)

    Returns:
        Created ShotPlanAsset
    """
    # Create job
    job = Job(
        job_id=generate_id("job_"),
        project_id=project_id,
        job_type=JobType.GENERATE_SHOTS,
        status=JobStatus.RUNNING,
        started_at=datetime.utcnow()
    )
    repository.create_job(job)

    try:
        project = repository.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Get plan
        if plan_asset_id is None:
            plan_asset_id = project.active_plan_asset_id

        if not plan_asset_id:
            raise ValueError("No plan asset specified and no active plan found")

        plan_id, plan_version = _parse_asset_ref(plan_asset_id)
        plan = repository.get_plan_asset(project_id, plan_id, plan_version)

        if not plan:
            raise ValueError(f"Plan {plan_asset_id} not found")

        # Call LLM
        client = get_gemini_client()
        prompt = GENERATE_SHOTS_PROMPT_V1.format(
            plan_json=json.dumps(plan.model_dump(), indent=2, default=str),
            target_duration_s=plan.project_bible.target_duration_s,
            pacing=plan.project_bible.pacing
        )

        result = client.generate_json(
            prompt=prompt,
            prompt_version=config.GENERATE_SHOTS_PROMPT_VERSION,
            project_id=project_id
        )

        # Parse result into ShotPlanAsset
        shot_plan = _parse_shot_plan_result(result, project_id, plan.plan_id, plan.version)

        # Validate and repair
        shot_plan = _validate_and_repair_shot_plan(plan, shot_plan, project_id)

        repository.create_shot_plan_asset(shot_plan)

        # Update project active pointer
        project.active_shot_plan_asset_id = build_asset_id(shot_plan.shot_plan_id, shot_plan.version)
        repository.update_project(project)

        # Update job
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.progress = 1.0
        job.output_refs = {"shot_plan_asset_id": build_asset_id(shot_plan.shot_plan_id, shot_plan.version)}
        repository.update_job(job)

        return shot_plan

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.utcnow()
        repository.update_job(job)
        raise


def _validate_and_repair_shot_plan(
    plan: PlanAsset,
    shot_plan: ShotPlanAsset,
    project_id: str
) -> ShotPlanAsset:
    """Validate shot plan and attempt repairs if needed."""
    for iteration in range(config.MAX_REPAIR_ITERATIONS):
        issues = validate_shot_plan(plan, shot_plan, use_llm_critic=(iteration == 0))

        # Filter to errors only
        errors = [issue for issue in issues if issue.severity == "error"]

        if not errors:
            # Valid!
            return shot_plan

        # Attempt repair
        repaired_json = repair_shot_plan(plan, shot_plan, errors, project_id)

        if repaired_json is None:
            # Repair failed, return with issues
            return shot_plan

        # Parse repaired JSON
        shot_plan = _parse_shot_plan_result(repaired_json, project_id, plan.plan_id, plan.version)

    # Max iterations reached, return best attempt
    return shot_plan


# ────────────────────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────────────────────

def _merge_preferences(preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge user preferences with defaults."""
    defaults = {
        "aspect_ratio": config.DEFAULT_ASPECT_RATIO,
        "target_duration_s": config.DEFAULT_TARGET_DURATION_S,
        "style": config.DEFAULT_STYLE,
        "pacing": config.DEFAULT_PACING,
        "visual_realism": config.DEFAULT_VISUAL_REALISM,
    }

    if preferences:
        defaults.update(preferences)

    return defaults


def _parse_plan_result(
    result: Dict[str, Any],
    project_id: str,
    script_id: str,
    script_version: int
) -> PlanAsset:
    """Parse LLM result into PlanAsset."""
    plan = PlanAsset(
        plan_id=generate_id("plan_"),
        version=1,
        source_script_id=script_id,
        source_script_version=script_version,
        project_id=project_id,
        project_bible=ProjectBible(**result["project_bible"]),
        characters=[Character(**char) for char in result.get("characters", [])],
        locations=[Location(**loc) for loc in result.get("locations", [])],
        props_wardrobe=[PropWardrobe(**prop) for prop in result.get("props_wardrobe", [])],
        scenes=[
            Scene(
                **{**scene, "beats": [Beat(**beat) for beat in scene.get("beats", [])]}
            )
            for scene in result.get("scenes", [])
        ]
    )

    return plan


def _parse_shot_plan_result(
    result: Dict[str, Any],
    project_id: str,
    plan_id: str,
    plan_version: int
) -> ShotPlanAsset:
    """Parse LLM result into ShotPlanAsset."""
    shots = []
    for shot_data in result.get("shots", []):
        # Parse camera
        camera_data = shot_data.get("camera", {})
        camera = CameraSetup(**camera_data)

        # Parse state_in and state_out
        state_in_data = shot_data.get("state_in", {})
        state_out_data = shot_data.get("state_out", {})
        state_in = StateDict(**state_in_data)
        state_out = StateDict(**state_out_data)

        shot = Shot(
            shot_id=shot_data["shot_id"],
            scene_id=shot_data["scene_id"],
            shot_index_in_scene=shot_data["shot_index_in_scene"],
            duration_s=shot_data["duration_s"],
            location_id=shot_data["location_id"],
            characters=shot_data.get("characters", []),
            shot_type=shot_data["shot_type"],
            camera=camera,
            action_beats=shot_data.get("action_beats", []),
            dialogue=shot_data.get("dialogue"),
            audio_notes=shot_data.get("audio_notes"),
            continuity_lock=shot_data.get("continuity_lock", ""),
            negative_prompt=shot_data.get("negative_prompt", ""),
            state_in=state_in,
            state_out=state_out
        )
        shots.append(shot)

    shot_plan = ShotPlanAsset(
        shot_plan_id=generate_id("shotplan_"),
        version=1,
        project_id=project_id,
        plan_id=plan_id,
        plan_version=plan_version,
        shots=shots
    )

    return shot_plan


def _parse_asset_ref(asset_ref: str) -> tuple[str, int]:
    """Parse asset reference into (stable_id, version)."""
    if '_v' in asset_ref:
        parts = asset_ref.rsplit('_v', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], int(parts[1])
    return asset_ref, 1
