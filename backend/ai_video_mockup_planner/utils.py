"""
Utility functions for AI Video Mockup Planner.
"""
import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, Optional


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    uid = str(uuid.uuid4())[:8]
    return f"{prefix}{uid}" if prefix else uid


def generate_timestamp() -> str:
    """Generate ISO timestamp string."""
    return datetime.utcnow().isoformat() + "Z"


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from text that may contain markdown code fences or extra text.
    Returns the first valid JSON object found, or None if parsing fails.
    """
    # Strip markdown code fences
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Try parsing directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON object from text
    # Look for first { and last }
    start = text.find('{')
    end = text.rfind('}')

    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


def format_duration(seconds: float) -> str:
    """Format duration in seconds to readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def safe_filename(name: str) -> str:
    """Convert string to safe filename."""
    # Replace unsafe characters
    safe = re.sub(r'[^\w\s-]', '', name)
    safe = re.sub(r'[-\s]+', '_', safe)
    return safe.lower()


def merge_dicts(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def validate_shot_id_format(shot_id: str) -> bool:
    """Validate shot ID format (e.g., S001, S002)."""
    return bool(re.match(r'^S\d{3,}$', shot_id))


def validate_scene_id_format(scene_id: str) -> bool:
    """Validate scene ID format (e.g., SC001, SC002)."""
    return bool(re.match(r'^SC\d{3,}$', scene_id))


def parse_asset_id(asset_id: str) -> tuple[str, int]:
    """
    Parse versioned asset ID into stable ID and version.
    Format: <stable_id>_v<version>
    Returns: (stable_id, version)
    """
    if '_v' in asset_id:
        parts = asset_id.rsplit('_v', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], int(parts[1])

    # If no version suffix, assume version 1
    return asset_id, 1


def build_asset_id(stable_id: str, version: int) -> str:
    """Build versioned asset ID from stable ID and version."""
    return f"{stable_id}_v{version}"
