"""
Local filesystem storage layer for AI Video Mockup Planner.
All assets are versioned and never overwritten.
Directory structure: {STORAGE_DIR}/{project_id}/...
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from .config import config
from .schemas import (
    Project, ScriptAsset, PlanAsset, ShotPlanAsset, ImageAsset,
    Job, LLMTrace, QAIssue, AssetStatus, JobStatus, ImageAssetType
)
from .utils import build_asset_id, parse_asset_id


class StorageRepository:
    """Repository for managing project assets on local filesystem."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or config.STORAGE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # ────────────────────────────────────────────────────────────────────────
    # PROJECTS
    # ────────────────────────────────────────────────────────────────────────

    def create_project(self, project: Project) -> Project:
        """Create a new project."""
        project_dir = self._get_project_dir(project.project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        # Initialize counters
        counters_path = project_dir / "_counters.json"
        counters = {
            "script_version": 0,
            "plan_version": 0,
            "shot_plan_version": 0,
            "image_version": 0,
            "job_number": 0,
            "trace_number": 0,
        }
        counters_path.write_text(json.dumps(counters, indent=2))

        # Save project metadata
        self._save_json(project_dir / "project.json", project.model_dump())
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieve project by ID."""
        project_path = self._get_project_dir(project_id) / "project.json"
        if not project_path.exists():
            return None
        data = self._load_json(project_path)
        return Project(**data)

    def update_project(self, project: Project) -> Project:
        """Update project metadata (active pointers, etc)."""
        project_path = self._get_project_dir(project.project_id) / "project.json"
        self._save_json(project_path, project.model_dump())
        return project

    def list_projects(self) -> List[Project]:
        """List all projects."""
        projects = []
        for project_dir in self.base_dir.iterdir():
            if project_dir.is_dir():
                project_path = project_dir / "project.json"
                if project_path.exists():
                    data = self._load_json(project_path)
                    projects.append(Project(**data))
        return projects

    # ────────────────────────────────────────────────────────────────────────
    # SCRIPT ASSETS
    # ────────────────────────────────────────────────────────────────────────

    def create_script_asset(self, script: ScriptAsset) -> ScriptAsset:
        """Create new versioned script asset."""
        project_dir = self._get_project_dir(script.project_id)
        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        asset_id = build_asset_id(script.script_id, script.version)
        path = scripts_dir / f"{asset_id}.json"
        self._save_json(path, script.model_dump())

        # Update index
        self._update_asset_index(scripts_dir, script.script_id, script.version)
        return script

    def get_script_asset(self, project_id: str, script_id: str, version: Optional[int] = None) -> Optional[ScriptAsset]:
        """Get script asset by ID and version (latest if None)."""
        if version is None:
            version = self._get_latest_version(project_id, "scripts", script_id)
            if version is None:
                return None

        asset_id = build_asset_id(script_id, version)
        path = self._get_project_dir(project_id) / "scripts" / f"{asset_id}.json"
        if not path.exists():
            return None
        data = self._load_json(path)
        return ScriptAsset(**data)

    def list_script_assets(self, project_id: str, script_id: Optional[str] = None) -> List[ScriptAsset]:
        """List all script assets for a project, optionally filtered by script_id."""
        scripts_dir = self._get_project_dir(project_id) / "scripts"
        if not scripts_dir.exists():
            return []

        scripts = []
        for path in scripts_dir.glob("*.json"):
            if path.name == "_index.json":
                continue
            data = self._load_json(path)
            script = ScriptAsset(**data)
            if script_id is None or script.script_id == script_id:
                scripts.append(script)

        return sorted(scripts, key=lambda s: (s.script_id, s.version))

    # ────────────────────────────────────────────────────────────────────────
    # PLAN ASSETS
    # ────────────────────────────────────────────────────────────────────────

    def create_plan_asset(self, plan: PlanAsset) -> PlanAsset:
        """Create new versioned plan asset."""
        project_dir = self._get_project_dir(plan.project_id)
        plans_dir = project_dir / "plans"
        plans_dir.mkdir(exist_ok=True)

        asset_id = build_asset_id(plan.plan_id, plan.version)
        path = plans_dir / f"{asset_id}.json"
        self._save_json(path, plan.model_dump())

        self._update_asset_index(plans_dir, plan.plan_id, plan.version)
        return plan

    def get_plan_asset(self, project_id: str, plan_id: str, version: Optional[int] = None) -> Optional[PlanAsset]:
        """Get plan asset by ID and version (latest if None)."""
        if version is None:
            version = self._get_latest_version(project_id, "plans", plan_id)
            if version is None:
                return None

        asset_id = build_asset_id(plan_id, version)
        path = self._get_project_dir(project_id) / "plans" / f"{asset_id}.json"
        if not path.exists():
            return None
        data = self._load_json(path)
        return PlanAsset(**data)

    def list_plan_assets(self, project_id: str, plan_id: Optional[str] = None) -> List[PlanAsset]:
        """List all plan assets for a project."""
        plans_dir = self._get_project_dir(project_id) / "plans"
        if not plans_dir.exists():
            return []

        plans = []
        for path in plans_dir.glob("*.json"):
            if path.name == "_index.json":
                continue
            data = self._load_json(path)
            plan = PlanAsset(**data)
            if plan_id is None or plan.plan_id == plan_id:
                plans.append(plan)

        return sorted(plans, key=lambda p: (p.plan_id, p.version))

    # ────────────────────────────────────────────────────────────────────────
    # SHOT PLAN ASSETS
    # ────────────────────────────────────────────────────────────────────────

    def create_shot_plan_asset(self, shot_plan: ShotPlanAsset) -> ShotPlanAsset:
        """Create new versioned shot plan asset."""
        project_dir = self._get_project_dir(shot_plan.project_id)
        shot_plans_dir = project_dir / "shot_plans"
        shot_plans_dir.mkdir(exist_ok=True)

        asset_id = build_asset_id(shot_plan.shot_plan_id, shot_plan.version)
        path = shot_plans_dir / f"{asset_id}.json"
        self._save_json(path, shot_plan.model_dump())

        self._update_asset_index(shot_plans_dir, shot_plan.shot_plan_id, shot_plan.version)
        return shot_plan

    def get_shot_plan_asset(self, project_id: str, shot_plan_id: str, version: Optional[int] = None) -> Optional[ShotPlanAsset]:
        """Get shot plan asset by ID and version (latest if None)."""
        if version is None:
            version = self._get_latest_version(project_id, "shot_plans", shot_plan_id)
            if version is None:
                return None

        asset_id = build_asset_id(shot_plan_id, version)
        path = self._get_project_dir(project_id) / "shot_plans" / f"{asset_id}.json"
        if not path.exists():
            return None
        data = self._load_json(path)
        return ShotPlanAsset(**data)

    def list_shot_plan_assets(self, project_id: str, shot_plan_id: Optional[str] = None) -> List[ShotPlanAsset]:
        """List all shot plan assets for a project."""
        shot_plans_dir = self._get_project_dir(project_id) / "shot_plans"
        if not shot_plans_dir.exists():
            return []

        shot_plans = []
        for path in shot_plans_dir.glob("*.json"):
            if path.name == "_index.json":
                continue
            data = self._load_json(path)
            shot_plan = ShotPlanAsset(**data)
            if shot_plan_id is None or shot_plan.shot_plan_id == shot_plan_id:
                shot_plans.append(shot_plan)

        return sorted(shot_plans, key=lambda sp: (sp.shot_plan_id, sp.version))

    # ────────────────────────────────────────────────────────────────────────
    # IMAGE ASSETS
    # ────────────────────────────────────────────────────────────────────────

    def create_image_asset(self, image: ImageAsset) -> ImageAsset:
        """Create new versioned image asset."""
        project_dir = self._get_project_dir(image.project_id)
        images_dir = project_dir / "images"
        images_dir.mkdir(exist_ok=True)

        asset_id = build_asset_id(image.image_id, image.version)
        path = images_dir / f"{asset_id}.json"
        self._save_json(path, image.model_dump())

        self._update_asset_index(images_dir, image.image_id, image.version)
        return image

    def get_image_asset(self, project_id: str, image_id: str, version: Optional[int] = None) -> Optional[ImageAsset]:
        """Get image asset by ID and version (latest if None)."""
        if version is None:
            version = self._get_latest_version(project_id, "images", image_id)
            if version is None:
                return None

        asset_id = build_asset_id(image_id, version)
        path = self._get_project_dir(project_id) / "images" / f"{asset_id}.json"
        if not path.exists():
            return None
        data = self._load_json(path)
        return ImageAsset(**data)

    def list_image_assets(
        self,
        project_id: str,
        asset_type: Optional[ImageAssetType] = None,
        status: Optional[AssetStatus] = None,
        shot_id: Optional[str] = None
    ) -> List[ImageAsset]:
        """List image assets with optional filters."""
        images_dir = self._get_project_dir(project_id) / "images"
        if not images_dir.exists():
            return []

        images = []
        for path in images_dir.glob("*.json"):
            if path.name == "_index.json":
                continue
            data = self._load_json(path)
            image = ImageAsset(**data)

            # Apply filters
            if asset_type is not None and image.asset_type != asset_type:
                continue
            if status is not None and image.status != status:
                continue
            if shot_id is not None and image.shot_id != shot_id:
                continue

            images.append(image)

        return sorted(images, key=lambda i: (i.image_id, i.version))

    # ────────────────────────────────────────────────────────────────────────
    # JOBS
    # ────────────────────────────────────────────────────────────────────────

    def create_job(self, job: Job) -> Job:
        """Create a new job."""
        project_dir = self._get_project_dir(job.project_id)
        jobs_dir = project_dir / "jobs"
        jobs_dir.mkdir(exist_ok=True)

        path = jobs_dir / f"{job.job_id}.json"
        self._save_json(path, job.model_dump())
        return job

    def update_job(self, job: Job) -> Job:
        """Update job status and progress."""
        project_dir = self._get_project_dir(job.project_id)
        jobs_dir = project_dir / "jobs"
        path = jobs_dir / f"{job.job_id}.json"
        self._save_json(path, job.model_dump())
        return job

    def get_job(self, project_id: str, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        path = self._get_project_dir(project_id) / "jobs" / f"{job_id}.json"
        if not path.exists():
            return None
        data = self._load_json(path)
        return Job(**data)

    def list_jobs(self, project_id: str, status: Optional[JobStatus] = None) -> List[Job]:
        """List jobs for a project, optionally filtered by status."""
        jobs_dir = self._get_project_dir(project_id) / "jobs"
        if not jobs_dir.exists():
            return []

        jobs = []
        for path in jobs_dir.glob("*.json"):
            data = self._load_json(path)
            job = Job(**data)
            if status is None or job.status == status:
                jobs.append(job)

        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    # ────────────────────────────────────────────────────────────────────────
    # LLM TRACES
    # ────────────────────────────────────────────────────────────────────────

    def save_llm_trace(self, project_id: str, trace: LLMTrace) -> LLMTrace:
        """Save LLM trace for debugging."""
        project_dir = self._get_project_dir(project_id)
        traces_dir = project_dir / "traces"
        traces_dir.mkdir(exist_ok=True)

        path = traces_dir / f"{trace.trace_id}.json"
        self._save_json(path, trace.model_dump())
        return trace

    def list_llm_traces(self, project_id: str, limit: int = 100) -> List[LLMTrace]:
        """List recent LLM traces."""
        traces_dir = self._get_project_dir(project_id) / "traces"
        if not traces_dir.exists():
            return []

        traces = []
        for path in sorted(traces_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            data = self._load_json(path)
            traces.append(LLMTrace(**data))

        return traces

    # ────────────────────────────────────────────────────────────────────────
    # HELPER METHODS
    # ────────────────────────────────────────────────────────────────────────

    def _get_project_dir(self, project_id: str) -> Path:
        """Get project directory path."""
        return self.base_dir / project_id

    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON from file."""
        return json.loads(path.read_text())

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Save JSON to file."""
        path.write_text(json.dumps(data, indent=2, default=str))

    def _update_asset_index(self, asset_dir: Path, stable_id: str, version: int) -> None:
        """Update asset index with latest version."""
        index_path = asset_dir / "_index.json"
        if index_path.exists():
            index = self._load_json(index_path)
        else:
            index = {}

        if stable_id not in index:
            index[stable_id] = {"versions": [], "latest": version}

        if version not in index[stable_id]["versions"]:
            index[stable_id]["versions"].append(version)
        index[stable_id]["latest"] = max(index[stable_id]["versions"])

        self._save_json(index_path, index)

    def _get_latest_version(self, project_id: str, asset_type: str, stable_id: str) -> Optional[int]:
        """Get latest version number for an asset."""
        index_path = self._get_project_dir(project_id) / asset_type / "_index.json"
        if not index_path.exists():
            return None

        index = self._load_json(index_path)
        if stable_id not in index:
            return None

        return index[stable_id]["latest"]

    def increment_counter(self, project_id: str, counter_name: str) -> int:
        """Increment and return project counter."""
        counters_path = self._get_project_dir(project_id) / "_counters.json"
        counters = self._load_json(counters_path)
        counters[counter_name] = counters.get(counter_name, 0) + 1
        self._save_json(counters_path, counters)
        return counters[counter_name]


# Global repository instance
repository = StorageRepository()
