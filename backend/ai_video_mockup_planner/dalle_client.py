"""
OpenAI DALL-E 3 client for generating images from prompts.
"""
from typing import Optional
import time

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .config import config


class DalleClient:
    """
    Wrapper for OpenAI DALL-E 3 API.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.OPENAI_API_KEY

        if not self.api_key or self.api_key == "stub_for_testing":
            self.client = None
            self.stub_mode = True
        elif OPENAI_AVAILABLE:
            self.client = OpenAI(api_key=self.api_key)
            self.stub_mode = False
        else:
            self.client = None
            self.stub_mode = True

    def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> str:
        """
        Generate an image from a text prompt using DALL-E 3.

        Args:
            prompt: The image description (max 4000 chars for DALL-E 3)
            size: Image size (1024x1024, 1792x1024, or 1024x1792)
            quality: Quality level (standard or hd)

        Returns:
            Image URL (hosted by OpenAI for 60 days)

        Raises:
            Exception: If generation fails
        """
        if self.stub_mode or not self.client:
            # Return placeholder in stub mode
            return f"placeholder://dalle_stub_{int(time.time())}.jpg"

        # Truncate prompt if too long (DALL-E 3 limit is 4000 chars)
        if len(prompt) > 4000:
            prompt = prompt[:3997] + "..."

        size = size or config.DALLE_SIZE
        quality = quality or config.DALLE_QUALITY

        try:
            response = self.client.images.generate(
                model=config.DALLE_MODEL,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )

            # Return the image URL
            return response.data[0].url

        except Exception as e:
            print(f"DALL-E 3 generation failed: {str(e)}")
            # Return placeholder on failure
            return f"placeholder://dalle_error_{int(time.time())}.jpg"


# Global client instance
_client: Optional[DalleClient] = None


def get_dalle_client() -> DalleClient:
    """Get or create global DALL-E client instance."""
    global _client
    if _client is None:
        _client = DalleClient()
    return _client
