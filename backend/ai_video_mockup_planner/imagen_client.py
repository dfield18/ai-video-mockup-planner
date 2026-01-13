"""
Google Imagen (Vertex AI) client for generating images from prompts.
"""
from typing import Optional
import time
import json
import os

try:
    from google.cloud import aiplatform
    from vertexai.preview.vision_models import ImageGenerationModel
    IMAGEN_AVAILABLE = True
except ImportError:
    IMAGEN_AVAILABLE = False

from .config import config


class ImagenClient:
    """
    Wrapper for Google Imagen via Vertex AI.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        credentials_json: Optional[str] = None
    ):
        self.project_id = project_id or config.GOOGLE_CLOUD_PROJECT_ID
        self.location = location or config.GOOGLE_CLOUD_LOCATION
        self.credentials_json = credentials_json or config.GOOGLE_CLOUD_CREDENTIALS_JSON

        # Check if we should use stub mode
        if not self.project_id or self.project_id == "stub_for_testing":
            self.model = None
            self.stub_mode = True
        elif not IMAGEN_AVAILABLE:
            print("Warning: google-cloud-aiplatform not installed. Using stub mode.")
            self.model = None
            self.stub_mode = True
        else:
            try:
                # Initialize Vertex AI
                if self.credentials_json:
                    # If credentials JSON is provided as a string (from env var)
                    # Write it to a temp file and set GOOGLE_APPLICATION_CREDENTIALS
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        if self.credentials_json.startswith('{'):
                            # It's JSON string
                            f.write(self.credentials_json)
                        else:
                            # It's a file path
                            with open(self.credentials_json, 'r') as cred_file:
                                f.write(cred_file.read())
                        credentials_path = f.name
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

                aiplatform.init(project=self.project_id, location=self.location)
                self.model = ImageGenerationModel.from_pretrained("imagegeneration@006")
                self.stub_mode = False
                print(f"✓ Imagen initialized (project: {self.project_id}, location: {self.location})")
            except Exception as e:
                print(f"Warning: Could not initialize Imagen: {str(e)}")
                print("Falling back to stub mode")
                self.model = None
                self.stub_mode = True

    def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        number_of_images: int = 1,
        aspect_ratio: str = "1:1",
    ) -> str:
        """
        Generate an image from a text prompt using Google Imagen.

        Args:
            prompt: The image description (max ~1000 words)
            negative_prompt: Things to avoid in the image
            number_of_images: Number of images to generate (we'll use first one)
            aspect_ratio: Image aspect ratio (1:1, 9:16, 16:9, 4:3, 3:4)

        Returns:
            Image URL or base64 data URI

        Raises:
            Exception: If generation fails
        """
        if self.stub_mode or not self.model:
            # Return placeholder in stub mode
            return f"placeholder://imagen_stub_{int(time.time())}.jpg"

        # Truncate prompt if too long (Imagen limit is ~1000 words)
        words = prompt.split()
        if len(words) > 900:
            prompt = ' '.join(words[:900]) + "..."

        try:
            # Generate image with Imagen
            response = self.model.generate_images(
                prompt=prompt,
                negative_prompt=negative_prompt,
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                safety_filter_level="block_some",
                person_generation="allow_adult",
            )

            # Get the first generated image
            image = response.images[0]

            # Imagen returns images as PIL Image objects
            # We need to convert to a URL or base64 data URI
            # For now, let's save to a temporary location and return a data URI
            import io
            import base64

            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image._pil_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            # Convert to base64 data URI
            base64_image = base64.b64encode(img_byte_arr).decode('utf-8')
            data_uri = f"data:image/png;base64,{base64_image}"

            return data_uri

        except Exception as e:
            print(f"Imagen generation failed: {str(e)}")
            # Return placeholder on failure
            return f"placeholder://imagen_error_{int(time.time())}.jpg"


# Global client instance
_client: Optional[ImagenClient] = None


def get_imagen_client() -> ImagenClient:
    """Get or create global Imagen client instance."""
    global _client
    if _client is None:
        _client = ImagenClient()
    return _client
