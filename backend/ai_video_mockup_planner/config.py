"""
Configuration management for AI Video Mockup Planner.
Loads from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    # Google AI
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-pro")  # Changed to more widely available model
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.4"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))

    # OpenAI (for image generation)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DALLE_MODEL: str = os.getenv("DALLE_MODEL", "dall-e-3")
    DALLE_SIZE: str = os.getenv("DALLE_SIZE", "1024x1024")  # Options: 1024x1024, 1792x1024, 1024x1792
    DALLE_QUALITY: str = os.getenv("DALLE_QUALITY", "standard")  # Options: standard, hd

    # Storage
    STORAGE_DIR: Path = Path(os.getenv("STORAGE_DIR", "./storage"))

    # Prompt versions
    EXTRACT_PLAN_PROMPT_VERSION: str = "v1"
    GENERATE_SHOTS_PROMPT_VERSION: str = "v1"
    CONTINUITY_CRITIC_PROMPT_VERSION: str = "v1"
    REPAIR_JSON_PROMPT_VERSION: str = "v1"
    INTERPRET_IMAGE_FEEDBACK_PROMPT_VERSION: str = "v1"
    BUILD_STYLE_FRAME_PROMPT_VERSION: str = "v1"
    BUILD_CHARACTER_REFERENCE_PROMPT_VERSION: str = "v1"
    BUILD_LOCATION_REFERENCE_PROMPT_VERSION: str = "v1"
    BUILD_SHOT_FRAME_PROMPT_VERSION: str = "v1"

    # Retry settings
    MAX_RETRIES: int = 3
    RETRY_WAIT_SECONDS: int = 2

    # Continuity repair
    MAX_REPAIR_ITERATIONS: int = 2

    # MVP defaults
    DEFAULT_ASPECT_RATIO: str = "16:9"
    DEFAULT_TARGET_DURATION_S: int = 30
    DEFAULT_STYLE: str = "cinematic realism"
    DEFAULT_PACING: str = "medium"
    DEFAULT_VISUAL_REALISM: str = "high"

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable is required")

        # Ensure storage directory exists
        cls.STORAGE_DIR.mkdir(parents=True, exist_ok=True)


config = Config()
