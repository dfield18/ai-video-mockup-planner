"""
Continuity validation and repair for shot plans.
Includes deterministic validators and optional LLM critic.
"""
import json
from typing import List, Dict, Any, Optional

from .schemas import PlanAsset, ShotPlanAsset, Shot, QAIssue, QAIssueSeverity
from .gemini_client import get_gemini_client
from .prompts import CONTINUITY_CRITIC_PROMPT_V1, REPAIR_JSON_PROMPT_V1
from .config import config


def validate_shot_plan(
    plan: PlanAsset,
    shot_plan: ShotPlanAsset,
    use_llm_critic: bool = True
) -> List[QAIssue]:
    """
    Validate shot plan for continuity issues.

    Args:
        plan: The plan asset with metadata
        shot_plan: The shot plan to validate
        use_llm_critic: Whether to use LLM critic (optional, slower)

    Returns:
        List of QA issues found
    """
    issues: List[QAIssue] = []

    # Run deterministic validators
    issues.extend(_validate_missing_entities(plan, shot_plan))
    issues.extend(_validate_uniqueness_and_order(shot_plan))
    issues.extend(_validate_required_fields(shot_plan))
    issues.extend(_validate_state_continuity(shot_plan))

    # Optionally run LLM critic
    if use_llm_critic and len(issues) < 10:  # Don't run if already many issues
        issues.extend(_run_llm_critic(plan, shot_plan))

    return issues


def repair_shot_plan(
    plan: PlanAsset,
    shot_plan: ShotPlanAsset,
    issues: List[QAIssue],
    project_id: str
) -> Optional[Dict[str, Any]]:
    """
    Attempt to repair shot plan using LLM.

    Args:
        plan: The plan asset
        shot_plan: The shot plan with issues
        issues: List of issues to fix
        project_id: Project ID for trace logging

    Returns:
        Repaired shot plan JSON, or None if repair failed
    """
    client = get_gemini_client()

    # Build repair prompt
    prompt = REPAIR_JSON_PROMPT_V1.format(
        broken_json=json.dumps(shot_plan.model_dump(), indent=2),
        qa_issues_json=json.dumps([issue.model_dump() for issue in issues], indent=2)
    )

    try:
        repaired = client.generate_json(
            prompt=prompt,
            prompt_version=config.REPAIR_JSON_PROMPT_VERSION,
            project_id=project_id,
            temperature=0.2  # Low temperature for repair
        )
        return repaired
    except Exception:
        return None


# ────────────────────────────────────────────────────────────────────────────────
# DETERMINISTIC VALIDATORS
# ────────────────────────────────────────────────────────────────────────────────

def _validate_missing_entities(plan: PlanAsset, shot_plan: ShotPlanAsset) -> List[QAIssue]:
    """Check for references to non-existent entities."""
    issues: List[QAIssue] = []

    # Build lookup sets
    character_ids = {char.character_id for char in plan.characters}
    location_ids = {loc.location_id for loc in plan.locations}
    scene_ids = {scene.scene_id for scene in plan.scenes}

    for shot in shot_plan.shots:
        # Check scene reference
        if shot.scene_id not in scene_ids:
            issues.append(QAIssue(
                severity=QAIssueSeverity.ERROR,
                issue_type="missing_entity",
                message=f"Shot {shot.shot_id} references non-existent scene {shot.scene_id}",
                suggested_fix=f"Ensure scene {shot.scene_id} exists in plan",
                shot_id=shot.shot_id
            ))

        # Check location reference
        if shot.location_id not in location_ids:
            issues.append(QAIssue(
                severity=QAIssueSeverity.ERROR,
                issue_type="missing_entity",
                message=f"Shot {shot.shot_id} references non-existent location {shot.location_id}",
                suggested_fix=f"Ensure location {shot.location_id} exists in plan",
                shot_id=shot.shot_id
            ))

        # Check character references
        for char_id in shot.characters:
            if char_id not in character_ids:
                issues.append(QAIssue(
                    severity=QAIssueSeverity.ERROR,
                    issue_type="missing_entity",
                    message=f"Shot {shot.shot_id} references non-existent character {char_id}",
                    suggested_fix=f"Ensure character {char_id} exists in plan",
                    shot_id=shot.shot_id
                ))

    return issues


def _validate_uniqueness_and_order(shot_plan: ShotPlanAsset) -> List[QAIssue]:
    """Check shot IDs are unique and shot_index_in_scene is sequential."""
    issues: List[QAIssue] = []

    # Check shot ID uniqueness
    shot_ids = [shot.shot_id for shot in shot_plan.shots]
    if len(shot_ids) != len(set(shot_ids)):
        duplicates = [sid for sid in shot_ids if shot_ids.count(sid) > 1]
        issues.append(QAIssue(
            severity=QAIssueSeverity.ERROR,
            issue_type="uniqueness",
            message=f"Duplicate shot IDs found: {', '.join(set(duplicates))}",
            suggested_fix="Ensure all shot IDs are unique"
        ))

    # Check shot_index_in_scene within each scene
    shots_by_scene: Dict[str, List[Shot]] = {}
    for shot in shot_plan.shots:
        if shot.scene_id not in shots_by_scene:
            shots_by_scene[shot.scene_id] = []
        shots_by_scene[shot.scene_id].append(shot)

    for scene_id, shots in shots_by_scene.items():
        indices = [shot.shot_index_in_scene for shot in shots]
        expected = list(range(len(shots)))
        if sorted(indices) != expected:
            issues.append(QAIssue(
                severity=QAIssueSeverity.WARNING,
                issue_type="order",
                message=f"Shot indices in scene {scene_id} are not sequential: {indices}",
                suggested_fix=f"Ensure shot_index_in_scene is 0, 1, 2, ... within scene {scene_id}"
            ))

    return issues


def _validate_required_fields(shot_plan: ShotPlanAsset) -> List[QAIssue]:
    """Check required fields are present and non-empty."""
    issues: List[QAIssue] = []

    for shot in shot_plan.shots:
        if not shot.continuity_lock or shot.continuity_lock.strip() == "":
            issues.append(QAIssue(
                severity=QAIssueSeverity.ERROR,
                issue_type="missing_field",
                message=f"Shot {shot.shot_id} is missing continuity_lock",
                suggested_fix="Add continuity_lock describing critical constraints for this shot",
                shot_id=shot.shot_id
            ))

        # negative_prompt can be empty, but should exist
        if shot.negative_prompt is None:
            issues.append(QAIssue(
                severity=QAIssueSeverity.WARNING,
                issue_type="missing_field",
                message=f"Shot {shot.shot_id} has no negative_prompt",
                suggested_fix="Add negative_prompt to avoid unwanted elements",
                shot_id=shot.shot_id
            ))

    return issues


def _validate_state_continuity(shot_plan: ShotPlanAsset) -> List[QAIssue]:
    """Check state_out of shot N matches state_in of shot N+1 within scenes."""
    issues: List[QAIssue] = []

    # Group shots by scene
    shots_by_scene: Dict[str, List[Shot]] = {}
    for shot in shot_plan.shots:
        if shot.scene_id not in shots_by_scene:
            shots_by_scene[shot.scene_id] = []
        shots_by_scene[shot.scene_id].append(shot)

    # Sort shots within each scene by shot_index_in_scene
    for scene_id in shots_by_scene:
        shots_by_scene[scene_id].sort(key=lambda s: s.shot_index_in_scene)

    # Check continuity within each scene
    for scene_id, shots in shots_by_scene.items():
        for i in range(len(shots) - 1):
            shot_current = shots[i]
            shot_next = shots[i + 1]

            state_out = shot_current.state_out
            state_in = shot_next.state_in

            # Check time_of_day
            if state_out.time_of_day and state_in.time_of_day:
                if state_out.time_of_day != state_in.time_of_day:
                    issues.append(QAIssue(
                        severity=QAIssueSeverity.WARNING,
                        issue_type="state_conflict",
                        message=f"Time of day changes unexpectedly between {shot_current.shot_id} (state_out: {state_out.time_of_day}) and {shot_next.shot_id} (state_in: {state_in.time_of_day})",
                        suggested_fix="Ensure time_of_day remains consistent within scene or add transition",
                        shot_id=shot_next.shot_id
                    ))

            # Check weather
            if state_out.weather and state_in.weather:
                if state_out.weather != state_in.weather:
                    issues.append(QAIssue(
                        severity=QAIssueSeverity.WARNING,
                        issue_type="state_conflict",
                        message=f"Weather changes unexpectedly between {shot_current.shot_id} (state_out: {state_out.weather}) and {shot_next.shot_id} (state_in: {state_in.weather})",
                        suggested_fix="Ensure weather remains consistent within scene",
                        shot_id=shot_next.shot_id
                    ))

            # Check props_held (should be similar or explained)
            props_out = set(state_out.props_held)
            props_in = set(state_in.props_held)
            if props_out != props_in:
                diff = props_out.symmetric_difference(props_in)
                issues.append(QAIssue(
                    severity=QAIssueSeverity.INFO,
                    issue_type="state_conflict",
                    message=f"Props held changes between {shot_current.shot_id} and {shot_next.shot_id}: {diff}",
                    suggested_fix="Ensure props changes are explained in action_beats",
                    shot_id=shot_next.shot_id
                ))

    return issues


def _run_llm_critic(plan: PlanAsset, shot_plan: ShotPlanAsset) -> List[QAIssue]:
    """Run LLM-based continuity critic (optional, slower)."""
    client = get_gemini_client()

    prompt = CONTINUITY_CRITIC_PROMPT_V1.format(
        plan_json=json.dumps(plan.model_dump(), indent=2, default=str),
        shot_plan_json=json.dumps(shot_plan.model_dump(), indent=2, default=str)
    )

    try:
        result = client.generate_json(
            prompt=prompt,
            prompt_version=config.CONTINUITY_CRITIC_PROMPT_VERSION,
            project_id=shot_plan.project_id,
            temperature=0.3
        )

        qa_issues = result.get("qa_issues", [])
        return [QAIssue(**issue) for issue in qa_issues]

    except Exception:
        # If LLM critic fails, just return empty list (deterministic checks already ran)
        return []
