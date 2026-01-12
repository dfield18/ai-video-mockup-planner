"""
Test that regeneration scopes affect only targeted shots/assets.
"""
import tempfile
from pathlib import Path

from ai_video_mockup_planner.storage import StorageRepository
from ai_video_mockup_planner.schemas import (
    Project, PlanAsset, ShotPlanAsset, Shot, ProjectBible,
    CameraSetup, StateDict, RegenScope, RegenScopeType, ImageAssetType
)
from ai_video_mockup_planner.image_pipeline import generate_images
from ai_video_mockup_planner.utils import build_asset_id


def test_shot_scope_regeneration(monkeypatch):
    """Test that shot-scoped regen only affects target shot."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = StorageRepository(Path(tmpdir))

        # Patch the global repository used by image_pipeline and gemini_client
        import ai_video_mockup_planner.image_pipeline as img_pipeline
        import ai_video_mockup_planner.storage as storage_module
        import ai_video_mockup_planner.gemini_client as gemini_module
        monkeypatch.setattr(img_pipeline, 'repository', repo)
        monkeypatch.setattr(storage_module, 'repository', repo)
        monkeypatch.setattr(gemini_module, 'repository', repo)

        # Create project
        project = Project(project_id="test_proj", title="Test")
        repo.create_project(project)

        # Create plan
        plan = PlanAsset(
            plan_id="plan_1",
            version=1,
            source_script_id="script_1",
            source_script_version=1,
            project_id="test_proj",
            project_bible=ProjectBible(
                title="Test",
                genre="Drama",
                tone="Serious",
                style="cinematic",
                aspect_ratio="16:9",
                target_duration_s=30,
                visual_realism="high",
                pacing="medium"
            )
        )
        repo.create_plan_asset(plan)

        # Create shot plan with multiple shots
        shot_plan = ShotPlanAsset(
            shot_plan_id="shotplan_1",
            version=1,
            project_id="test_proj",
            plan_id="plan_1",
            plan_version=1,
            shots=[
                Shot(
                    shot_id="S001",
                    scene_id="SC001",
                    shot_index_in_scene=0,
                    duration_s=3.0,
                    location_id="LOC_01",
                    characters=[],
                    shot_type="wide",
                    camera=CameraSetup(shot_type="wide"),
                    continuity_lock="Test",
                    state_in=StateDict(),
                    state_out=StateDict()
                ),
                Shot(
                    shot_id="S002",
                    scene_id="SC001",
                    shot_index_in_scene=1,
                    duration_s=3.0,
                    location_id="LOC_01",
                    characters=[],
                    shot_type="medium",
                    camera=CameraSetup(shot_type="medium"),
                    continuity_lock="Test",
                    state_in=StateDict(),
                    state_out=StateDict()
                ),
                Shot(
                    shot_id="S003",
                    scene_id="SC001",
                    shot_index_in_scene=2,
                    duration_s=3.0,
                    location_id="LOC_01",
                    characters=[],
                    shot_type="closeup",
                    camera=CameraSetup(shot_type="closeup"),
                    continuity_lock="Test",
                    state_in=StateDict(),
                    state_out=StateDict()
                )
            ]
        )
        repo.create_shot_plan_asset(shot_plan)

        # Update project pointers
        project.active_plan_asset_id = build_asset_id("plan_1", 1)
        project.active_shot_plan_asset_id = build_asset_id("shotplan_1", 1)
        repo.update_project(project)

        # Generate images for only S002
        scope = RegenScope(
            scope_type=RegenScopeType.SHOT,
            shot_id="S002"
        )

        images = generate_images("test_proj", scope)

        # Should generate only 1 image for S002
        assert len(images) == 1
        assert images[0].shot_id == "S002"

        # Verify other shots don't have images
        all_images = repo.list_image_assets("test_proj")
        shot_ids = [img.shot_id for img in all_images]
        assert "S002" in shot_ids
        assert "S001" not in shot_ids
        assert "S003" not in shot_ids


def test_scene_scope_regeneration(monkeypatch):
    """Test that scene-scoped regen affects all shots in scene."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = StorageRepository(Path(tmpdir))

        # Patch the global repository
        import ai_video_mockup_planner.image_pipeline as img_pipeline
        import ai_video_mockup_planner.storage as storage_module
        import ai_video_mockup_planner.gemini_client as gemini_module
        monkeypatch.setattr(img_pipeline, 'repository', repo)
        monkeypatch.setattr(storage_module, 'repository', repo)
        monkeypatch.setattr(gemini_module, 'repository', repo)

        # Create project
        project = Project(project_id="test_proj", title="Test")
        repo.create_project(project)

        # Create plan
        plan = PlanAsset(
            plan_id="plan_1",
            version=1,
            source_script_id="script_1",
            source_script_version=1,
            project_id="test_proj",
            project_bible=ProjectBible(
                title="Test",
                genre="Drama",
                tone="Serious",
                style="cinematic",
                aspect_ratio="16:9",
                target_duration_s=30,
                visual_realism="high",
                pacing="medium"
            )
        )
        repo.create_plan_asset(plan)

        # Create shot plan with shots in two scenes
        shot_plan = ShotPlanAsset(
            shot_plan_id="shotplan_1",
            version=1,
            project_id="test_proj",
            plan_id="plan_1",
            plan_version=1,
            shots=[
                Shot(
                    shot_id="S001",
                    scene_id="SC001",
                    shot_index_in_scene=0,
                    duration_s=3.0,
                    location_id="LOC_01",
                    characters=[],
                    shot_type="wide",
                    camera=CameraSetup(shot_type="wide"),
                    continuity_lock="Test",
                    state_in=StateDict(),
                    state_out=StateDict()
                ),
                Shot(
                    shot_id="S002",
                    scene_id="SC001",
                    shot_index_in_scene=1,
                    duration_s=3.0,
                    location_id="LOC_01",
                    characters=[],
                    shot_type="medium",
                    camera=CameraSetup(shot_type="medium"),
                    continuity_lock="Test",
                    state_in=StateDict(),
                    state_out=StateDict()
                ),
                Shot(
                    shot_id="S003",
                    scene_id="SC002",  # Different scene
                    shot_index_in_scene=0,
                    duration_s=3.0,
                    location_id="LOC_01",
                    characters=[],
                    shot_type="closeup",
                    camera=CameraSetup(shot_type="closeup"),
                    continuity_lock="Test",
                    state_in=StateDict(),
                    state_out=StateDict()
                )
            ]
        )
        repo.create_shot_plan_asset(shot_plan)

        # Update project pointers
        project.active_plan_asset_id = build_asset_id("plan_1", 1)
        project.active_shot_plan_asset_id = build_asset_id("shotplan_1", 1)
        repo.update_project(project)

        # Generate images for only SC001
        scope = RegenScope(
            scope_type=RegenScopeType.SCENE,
            scene_id="SC001"
        )

        images = generate_images("test_proj", scope)

        # Should generate 2 images for SC001 (S001 and S002)
        assert len(images) == 2
        shot_ids = [img.shot_id for img in images]
        assert "S001" in shot_ids
        assert "S002" in shot_ids
        assert "S003" not in shot_ids


def test_asset_type_scope_regeneration(monkeypatch):
    """Test that asset type scope affects only that asset type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = StorageRepository(Path(tmpdir))

        # Patch the global repository
        import ai_video_mockup_planner.image_pipeline as img_pipeline
        import ai_video_mockup_planner.storage as storage_module
        import ai_video_mockup_planner.gemini_client as gemini_module
        monkeypatch.setattr(img_pipeline, 'repository', repo)
        monkeypatch.setattr(storage_module, 'repository', repo)
        monkeypatch.setattr(gemini_module, 'repository', repo)

        # Create project
        project = Project(project_id="test_proj", title="Test")
        repo.create_project(project)

        # Create plan with characters and locations
        from ai_video_mockup_planner.schemas import Character, Location

        plan = PlanAsset(
            plan_id="plan_1",
            version=1,
            source_script_id="script_1",
            source_script_version=1,
            project_id="test_proj",
            project_bible=ProjectBible(
                title="Test",
                genre="Drama",
                tone="Serious",
                style="cinematic",
                aspect_ratio="16:9",
                target_duration_s=30,
                visual_realism="high",
                pacing="medium"
            ),
            characters=[
                Character(
                    character_id="CHAR_01",
                    name="Alice",
                    description="Protagonist",
                    identity_lock="Woman, 30s",
                    role="protagonist"
                )
            ],
            locations=[
                Location(
                    location_id="LOC_01",
                    name="Office",
                    description="Modern office",
                    location_lock="Glass walls"
                )
            ]
        )
        repo.create_plan_asset(plan)

        # Update project pointer
        project.active_plan_asset_id = build_asset_id("plan_1", 1)
        repo.update_project(project)

        # Generate only character references
        scope = RegenScope(
            scope_type=RegenScopeType.ASSET,
            asset_type=ImageAssetType.CHARACTER_REFERENCE
        )

        images = generate_images("test_proj", scope)

        # Should generate only character reference images
        assert len(images) == 1
        assert images[0].asset_type == ImageAssetType.CHARACTER_REFERENCE

        # Verify no location images created
        all_images = repo.list_image_assets("test_proj")
        asset_types = [img.asset_type for img in all_images]
        assert ImageAssetType.CHARACTER_REFERENCE in asset_types
        assert ImageAssetType.LOCATION_REFERENCE not in asset_types
