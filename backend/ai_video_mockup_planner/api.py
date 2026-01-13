"""
FastAPI application for AI Video Mockup Planner.
RESTful API for managing projects, scripts, plans, shots, and images.
"""
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from . import __version__
from .schemas import (
    Project, ScriptAsset, PlanAsset, ShotPlanAsset, ImageAsset, Job,
    CreateProjectRequest, CreateScriptRequest, GeneratePlanRequest,
    PatchPlanRequest, GenerateShotsRequest, GenerateImagesRequest,
    ImageActionRequest, ExportStoryboardRequest,
    AssetStatus, JobStatus, ImageAssetType
)
from .storage import repository
from . import pipeline
from .image_pipeline import generate_images, accept_image, edit_image, regenerate_image
from .exports import export_plan_json, export_characters_csv, export_shots_csv, export_storyboard


# ────────────────────────────────────────────────────────────────────────────────
# APP INITIALIZATION
# ────────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Video Mockup Planner",
    description="Production-ready system for generating structured shot plans and visual mockups",
    version=__version__
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ────────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


# ────────────────────────────────────────────────────────────────────────────────
# PROJECTS
# ────────────────────────────────────────────────────────────────────────────────

@app.post("/projects")
def create_project_endpoint(request: CreateProjectRequest):
    """Create a new project."""
    project = pipeline.create_project(request.title, request.user_id)
    return JSONResponse(content=jsonable_encoder(project))


@app.get("/projects/{project_id}", response_model=Project)
def get_project_endpoint(project_id: str):
    """Get project by ID."""
    project = pipeline.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project


@app.get("/projects", response_model=List[Project])
def list_projects_endpoint():
    """List all projects."""
    return repository.list_projects()


# ────────────────────────────────────────────────────────────────────────────────
# SCRIPTS
# ────────────────────────────────────────────────────────────────────────────────

@app.post("/script")
def create_script_endpoint(request: CreateScriptRequest):
    """Create or update a script."""
    # Check if we're updating an existing script
    project = repository.get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {request.project_id} not found")

    # For simplicity, always create new script (could enhance to detect updates)
    script = pipeline.create_script(
        request.project_id,
        request.content,
        request.title
    )
    return JSONResponse(content=jsonable_encoder(script))


@app.get("/script/{project_id}", response_model=ScriptAsset)
def get_active_script_endpoint(project_id: str):
    """Get active script for a project."""
    project = repository.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    if not project.active_script_asset_id:
        raise HTTPException(status_code=404, detail="No active script found")

    script_id, script_version = _parse_asset_ref(project.active_script_asset_id)
    script = repository.get_script_asset(project_id, script_id, script_version)

    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    return script


# ────────────────────────────────────────────────────────────────────────────────
# PLANS
# ────────────────────────────────────────────────────────────────────────────────

@app.post("/plan")
def generate_plan_endpoint(request: GeneratePlanRequest):
    """Generate a plan from script."""
    try:
        plan = pipeline.generate_plan(
            request.project_id,
            request.script_asset_id,
            request.preferences
        )
        return JSONResponse(content=jsonable_encoder(plan))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/plan/patch")
def patch_plan_endpoint(request: PatchPlanRequest):
    """Apply patches to plan, creating new version."""
    try:
        plan = pipeline.patch_plan(
            request.project_id,
            request.plan_asset_id,
            request.patches
        )
        return JSONResponse(content=jsonable_encoder(plan))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/plan/{project_id}", response_model=PlanAsset)
def get_active_plan_endpoint(project_id: str):
    """Get active plan for a project."""
    project = repository.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    if not project.active_plan_asset_id:
        raise HTTPException(status_code=404, detail="No active plan found")

    plan_id, plan_version = _parse_asset_ref(project.active_plan_asset_id)
    plan = repository.get_plan_asset(project_id, plan_id, plan_version)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return plan


# ────────────────────────────────────────────────────────────────────────────────
# SHOTS
# ────────────────────────────────────────────────────────────────────────────────

@app.post("/shots")
def generate_shots_endpoint(request: GenerateShotsRequest):
    """Generate shot plan from plan."""
    try:
        shot_plan = pipeline.generate_shots(
            request.project_id,
            request.plan_asset_id
        )
        return JSONResponse(content=jsonable_encoder(shot_plan))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/shots/{project_id}", response_model=ShotPlanAsset)
def get_active_shots_endpoint(project_id: str):
    """Get active shot plan for a project."""
    project = repository.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    if not project.active_shot_plan_asset_id:
        raise HTTPException(status_code=404, detail="No active shot plan found")

    shot_plan_id, shot_plan_version = _parse_asset_ref(project.active_shot_plan_asset_id)
    shot_plan = repository.get_shot_plan_asset(project_id, shot_plan_id, shot_plan_version)

    if not shot_plan:
        raise HTTPException(status_code=404, detail="Shot plan not found")

    return shot_plan


# ────────────────────────────────────────────────────────────────────────────────
# IMAGES
# ────────────────────────────────────────────────────────────────────────────────

@app.post("/images/generate")
def generate_images_endpoint(request: GenerateImagesRequest):
    """Generate images for a scope."""
    try:
        images = generate_images(
            request.project_id,
            request.scope,
            request.lock_profile
        )
        return JSONResponse(content=jsonable_encoder(images))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/image/action")
def image_action_endpoint(request: ImageActionRequest):
    """Perform action on image (accept/edit/regenerate)."""
    try:
        # Parse project_id from image_asset_id (need to look it up)
        # For now, we need project_id in the request
        # Let's extract from image by loading it
        image_id, version = _parse_asset_ref(request.image_asset_id)

        # Find project (search all projects for this image)
        project_id = _find_project_for_image(image_id)
        if not project_id:
            raise HTTPException(status_code=404, detail="Image not found")

        if request.action == "accept":
            image = accept_image(project_id, request.image_asset_id)
        elif request.action == "edit":
            if not request.feedback:
                raise HTTPException(status_code=400, detail="Feedback required for edit action")
            image = edit_image(project_id, request.image_asset_id, request.feedback, request.lock_profile)
        elif request.action == "regenerate":
            image = regenerate_image(project_id, request.image_asset_id, request.lock_profile)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

        return JSONResponse(content=jsonable_encoder(image))

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/assets/images", response_model=List[ImageAsset])
def list_images_endpoint(
    project_id: str = Query(...),
    asset_type: Optional[ImageAssetType] = Query(None),
    status: Optional[AssetStatus] = Query(None)
):
    """List image assets with optional filters."""
    images = repository.list_image_assets(
        project_id,
        asset_type=asset_type,
        status=status
    )
    return images


# ────────────────────────────────────────────────────────────────────────────────
# JOBS
# ────────────────────────────────────────────────────────────────────────────────

@app.get("/jobs/{job_id}", response_model=Job)
def get_job_endpoint(job_id: str, project_id: str = Query(...)):
    """Get job status by ID."""
    job = repository.get_job(project_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@app.get("/jobs", response_model=List[Job])
def list_jobs_endpoint(
    project_id: str = Query(...),
    status: Optional[JobStatus] = Query(None)
):
    """List jobs for a project."""
    jobs = repository.list_jobs(project_id, status)
    return jobs


# ────────────────────────────────────────────────────────────────────────────────
# EXPORTS
# ────────────────────────────────────────────────────────────────────────────────

@app.get("/export/plan/{project_id}")
def export_plan_endpoint(project_id: str):
    """Export plan as JSON."""
    try:
        plan_json = export_plan_json(project_id)
        return plan_json
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/export/characters/{project_id}")
def export_characters_endpoint(project_id: str):
    """Export characters as CSV-ready data."""
    try:
        characters = export_characters_csv(project_id)
        return {"rows": characters}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/export/shots/{project_id}")
def export_shots_endpoint(project_id: str):
    """Export shots as CSV-ready data."""
    try:
        shots = export_shots_csv(project_id)
        return {"rows": shots}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/export/storyboard")
def export_storyboard_endpoint(request: ExportStoryboardRequest):
    """Export complete storyboard."""
    try:
        storyboard = export_storyboard(
            request.project_id,
            request.include_images,
            request.format
        )
        return storyboard
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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


def _find_project_for_image(image_id: str) -> Optional[str]:
    """Find project ID for a given image ID."""
    # Iterate through all projects
    projects = repository.list_projects()
    for project in projects:
        images = repository.list_image_assets(project.project_id)
        for image in images:
            if image.image_id == image_id:
                return project.project_id
    return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
