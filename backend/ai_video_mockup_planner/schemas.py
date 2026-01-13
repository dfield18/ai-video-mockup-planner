"""
Core Pydantic schemas for AI Video Mockup Planner.
All assets are versioned and immutable.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ────────────────────────────────────────────────────────────────────────────────
# ENUMS
# ────────────────────────────────────────────────────────────────────────────────

class AssetStatus(str, Enum):
    DRAFT = "draft"
    ACCEPTED = "accepted"
    ARCHIVED = "archived"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    EXTRACT_PLAN = "extract_plan"
    GENERATE_SHOTS = "generate_shots"
    GENERATE_IMAGES = "generate_images"
    EDIT_IMAGE = "edit_image"
    REGENERATE_IMAGE = "regenerate_image"


class ImageAssetType(str, Enum):
    CHARACTER_REFERENCE = "character_reference"
    LOCATION_REFERENCE = "location_reference"
    SHOT_FRAME = "shot_frame"
    STYLE_FRAME = "style_frame"
    PROP_REFERENCE = "prop_reference"


class RegenScopeType(str, Enum):
    PROJECT = "project"
    SCENE = "scene"
    SHOT = "shot"
    ASSET = "asset"


class QAIssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ────────────────────────────────────────────────────────────────────────────────
# CORE ASSETS
# ────────────────────────────────────────────────────────────────────────────────

class Project(BaseModel):
    """Top-level project container."""
    project_id: str
    user_id: Optional[str] = None
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Active asset pointers (latest accepted or draft)
    active_script_asset_id: Optional[str] = None
    active_plan_asset_id: Optional[str] = None
    active_shot_plan_asset_id: Optional[str] = None
    active_style_frame_image_asset_id: Optional[str] = None


class ScriptAsset(BaseModel):
    """Versioned script asset."""
    script_id: str  # Stable ID across versions
    version: int
    content: str
    title: Optional[str] = None
    language: str = "en"
    parent_script_asset_id: Optional[str] = None  # Previous version ref
    status: AssetStatus = AssetStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    project_id: str


class ProjectBible(BaseModel):
    """High-level project metadata."""
    title: str
    genre: str
    tone: str
    style: str
    aspect_ratio: str = "16:9"
    target_duration_s: int = 30
    visual_realism: str = "high"
    pacing: str = "medium"


class Character(BaseModel):
    """Character definition with identity lock."""
    character_id: str
    name: str
    description: str
    identity_lock: str  # Detailed description for image generation
    wardrobe_lock: Optional[str] = None
    key_props: List[str] = Field(default_factory=list)
    role: Optional[str] = None


class Location(BaseModel):
    """Location definition with layout lock."""
    location_id: str
    name: str
    description: str
    location_lock: str  # Detailed description for continuity
    time_of_day: Optional[str] = None
    weather: Optional[str] = None


class PropWardrobe(BaseModel):
    """Props and wardrobe items."""
    prop_id: str
    name: str
    description: str
    category: str  # "prop" | "wardrobe" | "vehicle" | "weapon"


class Beat(BaseModel):
    """Story beat within a scene."""
    beat_index: int
    action: str
    emotional_tone: Optional[str] = None


class Scene(BaseModel):
    """Scene definition."""
    scene_id: str
    scene_index: int
    summary: str
    location_id: str
    time_of_day: str
    beats: List[Beat] = Field(default_factory=list)
    characters_present: List[str] = Field(default_factory=list)


class PlanAsset(BaseModel):
    """Versioned plan asset containing all structured metadata."""
    plan_id: str  # Stable ID
    version: int
    schema_version: str = "1.0"
    source_script_id: str
    source_script_version: int
    status: AssetStatus = AssetStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    parent_plan_asset_id: Optional[str] = None
    project_id: str

    # Embedded structured data
    project_bible: ProjectBible
    characters: List[Character] = Field(default_factory=list)
    locations: List[Location] = Field(default_factory=list)
    props_wardrobe: List[PropWardrobe] = Field(default_factory=list)
    scenes: List[Scene] = Field(default_factory=list)


class CameraSetup(BaseModel):
    """Camera parameters for a shot."""
    shot_type: str  # "wide" | "medium" | "closeup" | "extreme_closeup" | "over_shoulder"
    angle: str = "eye_level"  # "high" | "eye_level" | "low" | "dutch"
    movement: str = "static"  # "static" | "pan" | "tilt" | "dolly" | "track" | "handheld"
    lens: Optional[str] = None


class StateDict(BaseModel):
    """State tracking for continuity (props, wardrobe, injuries, etc)."""
    props_held: List[str] = Field(default_factory=list)
    wardrobe_state: Dict[str, str] = Field(default_factory=dict)  # character_id -> description
    injuries_visible: List[str] = Field(default_factory=list)
    time_of_day: Optional[str] = None
    weather: Optional[str] = None
    custom: Dict[str, Any] = Field(default_factory=dict)


class Shot(BaseModel):
    """Individual shot definition."""
    shot_id: str
    scene_id: str
    shot_index_in_scene: int
    duration_s: float
    location_id: str
    characters: List[str] = Field(default_factory=list)
    shot_type: str
    camera: CameraSetup
    action_beats: List[str] = Field(default_factory=list)
    dialogue: Optional[str] = None
    audio_notes: Optional[str] = None
    continuity_lock: str  # MUST be present; critical constraints
    negative_prompt: str = ""
    state_in: StateDict = Field(default_factory=StateDict)
    state_out: StateDict = Field(default_factory=StateDict)
    veo_prompt: Optional[str] = None  # Built separately


class ShotPlanAsset(BaseModel):
    """Versioned shot plan asset."""
    shot_plan_id: str
    version: int
    status: AssetStatus = AssetStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    parent_shot_plan_asset_id: Optional[str] = None
    project_id: str
    plan_id: str
    plan_version: int

    shots: List[Shot] = Field(default_factory=list)


class LockProfile(BaseModel):
    """Controls what must remain constant during regeneration."""
    preserve_identity: bool = True
    preserve_wardrobe: bool = True
    preserve_style: bool = True
    preserve_camera: bool = False
    preserve_pose: bool = False
    preserve_location_layout: bool = True
    preserve_time_of_day: bool = True
    banned_elements: List[str] = Field(default_factory=list)
    must_keep_elements: List[str] = Field(default_factory=list)


class ImageAsset(BaseModel):
    """Versioned image asset."""
    image_id: str  # Stable ID
    version: int
    asset_type: ImageAssetType

    # Source references
    project_id: str
    plan_id: Optional[str] = None
    shot_plan_id: Optional[str] = None
    shot_id: Optional[str] = None
    character_ids: List[str] = Field(default_factory=list)
    location_id: Optional[str] = None

    # Image data
    image_url: str  # For MVP: "placeholder://..." or local path
    prompt_used: str
    negative_prompt: str = ""

    # Lock profile for regeneration
    lock_profile: LockProfile = Field(default_factory=LockProfile)

    status: AssetStatus = AssetStatus.DRAFT
    parent_image_asset_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RegenScope(BaseModel):
    """Defines scope for regeneration operations."""
    scope_type: RegenScopeType
    scene_id: Optional[str] = None
    shot_id: Optional[str] = None
    asset_type: Optional[ImageAssetType] = None
    target_image_id: Optional[str] = None


class Job(BaseModel):
    """Async job tracking."""
    job_id: str
    project_id: str
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0  # 0.0 to 1.0
    message: str = ""
    input_refs: Dict[str, Any] = Field(default_factory=dict)
    output_refs: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class QAIssue(BaseModel):
    """Quality assurance issue."""
    severity: QAIssueSeverity
    issue_type: str
    message: str
    suggested_fix: Optional[str] = None
    shot_id: Optional[str] = None
    image_id: Optional[str] = None


class LLMTrace(BaseModel):
    """LLM call tracing for debugging."""
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    prompt_version: str
    prompt_text: str
    payload_json: Dict[str, Any]
    raw_response_text: str
    parsed_json: Optional[Dict[str, Any]] = None
    parse_error: Optional[str] = None
    retry_count: int = 0


# ────────────────────────────────────────────────────────────────────────────────
# API REQUEST/RESPONSE MODELS
# ────────────────────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    title: str
    user_id: Optional[str] = None


class CreateScriptRequest(BaseModel):
    project_id: str
    content: str
    title: Optional[str] = None


class GeneratePlanRequest(BaseModel):
    project_id: str
    script_asset_id: Optional[str] = None  # If None, use active
    preferences: Optional[Dict[str, Any]] = None


class PatchPlanRequest(BaseModel):
    project_id: str
    plan_asset_id: Optional[str] = None  # If None, use active
    patches: List[Dict[str, Any]]  # JSONPath-style patches


class GenerateShotsRequest(BaseModel):
    project_id: str
    plan_asset_id: Optional[str] = None


class GenerateImagesRequest(BaseModel):
    project_id: str
    scope: RegenScope
    lock_profile: Optional[LockProfile] = None


class ImageActionRequest(BaseModel):
    action: str  # "accept" | "edit" | "regenerate"
    image_asset_id: str
    feedback: Optional[str] = None  # For edit action
    lock_profile: Optional[LockProfile] = None  # For regenerate


class ExportStoryboardRequest(BaseModel):
    project_id: str
    include_images: bool = True
    format: str = "json"  # "json" | "csv"
