"""
Test that versioning works correctly and assets are never overwritten.
"""
import tempfile
from pathlib import Path

from ai_video_mockup_planner.storage import StorageRepository
from ai_video_mockup_planner.schemas import (
    Project, ScriptAsset, PlanAsset, ProjectBible, AssetStatus
)
from ai_video_mockup_planner.utils import build_asset_id


def test_script_versioning():
    """Test that scripts are versioned and never overwritten."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = StorageRepository(Path(tmpdir))

        # Create project
        project = Project(project_id="test_proj", title="Test")
        repo.create_project(project)

        # Create script v1
        script_v1 = ScriptAsset(
            script_id="script_1",
            version=1,
            content="Version 1 content",
            project_id="test_proj"
        )
        repo.create_script_asset(script_v1)

        # Create script v2
        script_v2 = ScriptAsset(
            script_id="script_1",
            version=2,
            content="Version 2 content",
            parent_script_asset_id=build_asset_id("script_1", 1),
            project_id="test_proj"
        )
        repo.create_script_asset(script_v2)

        # Verify both versions exist
        retrieved_v1 = repo.get_script_asset("test_proj", "script_1", 1)
        retrieved_v2 = repo.get_script_asset("test_proj", "script_1", 2)

        assert retrieved_v1 is not None
        assert retrieved_v2 is not None
        assert retrieved_v1.content == "Version 1 content"
        assert retrieved_v2.content == "Version 2 content"

        # Verify latest version
        latest = repo.get_script_asset("test_proj", "script_1")
        assert latest.version == 2
        assert latest.content == "Version 2 content"


def test_plan_versioning():
    """Test that plans are versioned and never overwritten."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = StorageRepository(Path(tmpdir))

        # Create project
        project = Project(project_id="test_proj", title="Test")
        repo.create_project(project)

        # Create plan v1
        plan_v1 = PlanAsset(
            plan_id="plan_1",
            version=1,
            source_script_id="script_1",
            source_script_version=1,
            project_id="test_proj",
            project_bible=ProjectBible(
                title="Test Plan V1",
                genre="Drama",
                tone="Serious",
                style="cinematic",
                aspect_ratio="16:9",
                target_duration_s=30,
                visual_realism="high",
                pacing="medium"
            )
        )
        repo.create_plan_asset(plan_v1)

        # Create plan v2 (patched)
        plan_v2 = PlanAsset(
            plan_id="plan_1",
            version=2,
            source_script_id="script_1",
            source_script_version=1,
            project_id="test_proj",
            parent_plan_asset_id=build_asset_id("plan_1", 1),
            project_bible=ProjectBible(
                title="Test Plan V2 (Edited)",
                genre="Drama",
                tone="Serious",
                style="cinematic",
                aspect_ratio="16:9",
                target_duration_s=30,
                visual_realism="high",
                pacing="medium"
            )
        )
        repo.create_plan_asset(plan_v2)

        # Verify both versions exist
        retrieved_v1 = repo.get_plan_asset("test_proj", "plan_1", 1)
        retrieved_v2 = repo.get_plan_asset("test_proj", "plan_1", 2)

        assert retrieved_v1 is not None
        assert retrieved_v2 is not None
        assert retrieved_v1.project_bible.title == "Test Plan V1"
        assert retrieved_v2.project_bible.title == "Test Plan V2 (Edited)"


def test_image_versioning():
    """Test that images are versioned and never overwritten."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = StorageRepository(Path(tmpdir))

        # Create project
        project = Project(project_id="test_proj", title="Test")
        repo.create_project(project)

        from ai_video_mockup_planner.schemas import ImageAsset, ImageAssetType, LockProfile

        # Create image v1
        image_v1 = ImageAsset(
            image_id="img_1",
            version=1,
            asset_type=ImageAssetType.SHOT_FRAME,
            project_id="test_proj",
            image_url="placeholder://v1.jpg",
            prompt_used="Original prompt",
            negative_prompt="low quality",
            lock_profile=LockProfile()
        )
        repo.create_image_asset(image_v1)

        # Create image v2 (edited)
        image_v2 = ImageAsset(
            image_id="img_1",
            version=2,
            asset_type=ImageAssetType.SHOT_FRAME,
            project_id="test_proj",
            image_url="placeholder://v2.jpg",
            prompt_used="Edited prompt",
            negative_prompt="low quality",
            parent_image_asset_id=build_asset_id("img_1", 1),
            lock_profile=LockProfile()
        )
        repo.create_image_asset(image_v2)

        # Verify both versions exist
        retrieved_v1 = repo.get_image_asset("test_proj", "img_1", 1)
        retrieved_v2 = repo.get_image_asset("test_proj", "img_1", 2)

        assert retrieved_v1 is not None
        assert retrieved_v2 is not None
        assert retrieved_v1.image_url == "placeholder://v1.jpg"
        assert retrieved_v2.image_url == "placeholder://v2.jpg"
        assert retrieved_v1.prompt_used == "Original prompt"
        assert retrieved_v2.prompt_used == "Edited prompt"
