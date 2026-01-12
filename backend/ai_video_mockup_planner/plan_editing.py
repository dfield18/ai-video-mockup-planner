"""
Plan editing and patching functionality.
Supports PATCH-like operations on PlanAsset.
"""
from typing import Any, Dict, List
from copy import deepcopy

from .schemas import PlanAsset, Character, Location, ProjectBible


def apply_patches(plan: PlanAsset, patches: List[Dict[str, Any]]) -> PlanAsset:
    """
    Apply a list of patches to a plan asset.

    Each patch is a dict with:
    - path: JSONPath-like string (e.g., "characters[0].identity_lock")
    - op: "replace" | "add" | "remove"
    - value: new value (for replace/add)

    Returns:
        New PlanAsset with patches applied (original is not modified)
    """
    # Deep copy to avoid mutating original
    plan_dict = plan.model_dump()

    for patch in patches:
        path = patch.get("path", "")
        op = patch.get("op", "replace")
        value = patch.get("value")

        plan_dict = _apply_single_patch(plan_dict, path, op, value)

    # Reconstruct PlanAsset
    return PlanAsset(**plan_dict)


def _apply_single_patch(data: Dict[str, Any], path: str, op: str, value: Any) -> Dict[str, Any]:
    """
    Apply a single patch to nested dict.

    Path format examples:
    - "project_bible.title"
    - "characters[0].identity_lock"
    - "locations[LOC_01].location_lock"
    """
    if not path:
        return data

    # Parse path
    parts = _parse_path(path)

    # Navigate to target
    current = data
    for i, part in enumerate(parts[:-1]):
        if isinstance(part, str):
            # Dict key
            if part not in current:
                current[part] = {}
            current = current[part]
        elif isinstance(part, int):
            # List index
            current = current[part]
        else:
            # ID-based lookup (e.g., "characters[CHAR_01]")
            list_key, item_id = part
            items = current.get(list_key, [])
            # Find item by ID
            id_field = _get_id_field_for_list(list_key)
            found = None
            for item in items:
                if item.get(id_field) == item_id:
                    found = item
                    break
            if found is None:
                raise ValueError(f"Item with ID {item_id} not found in {list_key}")
            current = found

    # Apply operation on final part
    final_part = parts[-1]

    if op == "replace":
        if isinstance(final_part, str):
            current[final_part] = value
        elif isinstance(final_part, int):
            current[final_part] = value
        else:
            list_key, item_id = final_part
            id_field = _get_id_field_for_list(list_key)
            items = current.get(list_key, [])
            for i, item in enumerate(items):
                if item.get(id_field) == item_id:
                    items[i] = value
                    break

    elif op == "add":
        if isinstance(final_part, str):
            # Adding to dict
            if isinstance(current[final_part], list):
                current[final_part].append(value)
            else:
                current[final_part] = value
        else:
            raise ValueError(f"Cannot add to path: {path}")

    elif op == "remove":
        if isinstance(final_part, str):
            if final_part in current:
                del current[final_part]
        elif isinstance(final_part, int):
            # Remove from list
            parent = current
            parent.pop(final_part)
        else:
            list_key, item_id = final_part
            id_field = _get_id_field_for_list(list_key)
            items = current.get(list_key, [])
            current[list_key] = [item for item in items if item.get(id_field) != item_id]

    return data


def _parse_path(path: str) -> List[Any]:
    """
    Parse path into parts.

    Examples:
    - "project_bible.title" -> ["project_bible", "title"]
    - "characters[0].identity_lock" -> ["characters", 0, "identity_lock"]
    - "characters[CHAR_01].identity_lock" -> [("characters", "CHAR_01"), "identity_lock"]
    """
    parts = []
    current = ""
    i = 0

    while i < len(path):
        char = path[i]

        if char == '.':
            if current:
                parts.append(current)
                current = ""
            i += 1

        elif char == '[':
            # Array access
            if current:
                list_key = current
                current = ""

            # Find closing ]
            j = path.index(']', i)
            index_str = path[i + 1:j]

            # Check if numeric or ID
            if index_str.isdigit():
                parts.append(list_key)
                parts.append(int(index_str))
            else:
                # ID-based lookup
                parts.append((list_key, index_str))

            i = j + 1

        else:
            current += char
            i += 1

    if current:
        parts.append(current)

    return parts


def _get_id_field_for_list(list_key: str) -> str:
    """Get the ID field name for a given list."""
    mapping = {
        "characters": "character_id",
        "locations": "location_id",
        "props_wardrobe": "prop_id",
        "scenes": "scene_id",
    }
    return mapping.get(list_key, "id")


# ────────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTIONS
# ────────────────────────────────────────────────────────────────────────────────

def update_character(
    plan: PlanAsset,
    character_id: str,
    updates: Dict[str, Any]
) -> PlanAsset:
    """
    Update a character's fields.

    Args:
        plan: The plan asset
        character_id: Character ID to update
        updates: Dict of field -> new value

    Returns:
        New PlanAsset with character updated
    """
    patches = []
    for field, value in updates.items():
        patches.append({
            "path": f"characters[{character_id}].{field}",
            "op": "replace",
            "value": value
        })

    return apply_patches(plan, patches)


def update_location(
    plan: PlanAsset,
    location_id: str,
    updates: Dict[str, Any]
) -> PlanAsset:
    """Update a location's fields."""
    patches = []
    for field, value in updates.items():
        patches.append({
            "path": f"locations[{location_id}].{field}",
            "op": "replace",
            "value": value
        })

    return apply_patches(plan, patches)


def update_project_bible(
    plan: PlanAsset,
    updates: Dict[str, Any]
) -> PlanAsset:
    """Update project bible fields."""
    patches = []
    for field, value in updates.items():
        patches.append({
            "path": f"project_bible.{field}",
            "op": "replace",
            "value": value
        })

    return apply_patches(plan, patches)
