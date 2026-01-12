"""
Google Gemini API client wrapper with retry logic and trace logging.
"""
import json
from typing import Any, Dict, Optional
from datetime import datetime

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from tenacity import retry, stop_after_attempt, wait_exponential

from .config import config
from .schemas import LLMTrace
from .storage import repository
from .utils import extract_json_from_text, generate_id


class GeminiClient:
    """
    Wrapper for Google Gemini API with JSON parsing and trace logging.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.GOOGLE_API_KEY
        self.model_name = model or config.GEMINI_MODEL

        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY must be provided")

        if GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None

    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=config.RETRY_WAIT_SECONDS, max=10)
    )
    def generate_json(
        self,
        prompt: str,
        prompt_version: str,
        project_id: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate JSON response from Gemini.
        Retries on failure, logs traces, attempts JSON repair if parsing fails.

        Args:
            prompt: The prompt text
            prompt_version: Version identifier for the prompt
            project_id: Project ID for trace logging
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            Parsed JSON dict

        Raises:
            Exception: If generation or parsing fails after retries
        """
        trace_id = generate_id("trace_")
        temp = temperature if temperature is not None else config.TEMPERATURE
        max_tok = max_tokens if max_tokens is not None else config.MAX_TOKENS

        payload = {
            "prompt": prompt,
            "temperature": temp,
            "max_tokens": max_tok,
        }

        # Generate response
        try:
            if self.model is None:
                # Stub mode for testing without API key
                raw_response = self._stub_response(prompt)
            else:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temp,
                        max_output_tokens=max_tok,
                    )
                )
                raw_response = response.text

        except Exception as e:
            # Log failed trace
            trace = LLMTrace(
                trace_id=trace_id,
                prompt_version=prompt_version,
                prompt_text=prompt,
                payload_json=payload,
                raw_response_text="",
                parsed_json=None,
                parse_error=f"API error: {str(e)}",
                retry_count=0,
            )
            repository.save_llm_trace(project_id, trace)
            raise

        # Parse JSON
        parsed = extract_json_from_text(raw_response)

        if parsed is None:
            # JSON parsing failed, log and try repair
            trace = LLMTrace(
                trace_id=trace_id,
                prompt_version=prompt_version,
                prompt_text=prompt,
                payload_json=payload,
                raw_response_text=raw_response,
                parsed_json=None,
                parse_error="Failed to extract JSON from response",
                retry_count=0,
            )
            repository.save_llm_trace(project_id, trace)

            # Attempt repair
            parsed = self._attempt_json_repair(raw_response, project_id)

            if parsed is None:
                raise ValueError(f"Failed to parse JSON from Gemini response: {raw_response[:200]}")

        # Log successful trace
        trace = LLMTrace(
            trace_id=trace_id,
            prompt_version=prompt_version,
            prompt_text=prompt,
            payload_json=payload,
            raw_response_text=raw_response,
            parsed_json=parsed,
            parse_error=None,
            retry_count=0,
        )
        repository.save_llm_trace(project_id, trace)

        return parsed

    def _attempt_json_repair(self, broken_text: str, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to repair broken JSON by asking Gemini to fix it.
        """
        from .prompts import REPAIR_JSON_PROMPT_V1

        repair_prompt = REPAIR_JSON_PROMPT_V1.format(
            broken_json=broken_text,
            qa_issues_json=json.dumps({"issues": ["Invalid JSON format"]}, indent=2)
        )

        try:
            if self.model is None:
                return None

            response = self.model.generate_content(
                repair_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temperature for repair
                    max_output_tokens=config.MAX_TOKENS,
                )
            )
            repaired = extract_json_from_text(response.text)
            return repaired

        except Exception:
            return None

    def _stub_response(self, prompt: str) -> str:
        """
        Generate a stub response for testing without API key.
        Returns minimal valid JSON based on prompt type.
        """
        if "EXTRACT_PLAN" in prompt or "project_bible" in prompt:
            return json.dumps({
                "schema_version": "1.0",
                "project_bible": {
                    "title": "Test Project",
                    "genre": "Drama",
                    "tone": "Serious",
                    "style": "cinematic realism",
                    "aspect_ratio": "16:9",
                    "target_duration_s": 30,
                    "visual_realism": "high",
                    "pacing": "medium"
                },
                "characters": [],
                "locations": [],
                "props_wardrobe": [],
                "scenes": []
            })
        elif "GENERATE_SHOTS" in prompt or "shots" in prompt.lower():
            return json.dumps({
                "schema_version": "1.0",
                "shots": []
            })
        elif "qa_issues" in prompt.lower():
            return json.dumps({
                "schema_version": "1.0",
                "qa_issues": []
            })
        elif "edit_delta" in prompt.lower():
            return json.dumps({
                "schema_version": "1.0",
                "edit_delta": {
                    "add_elements": [],
                    "remove_elements": [],
                    "modify_elements": [],
                    "style_adjustments": [],
                    "camera_adjustments": {}
                },
                "updated_prompt_guidance": "No changes"
            })
        elif "prompt" in prompt.lower() and "negative_prompt" in prompt.lower():
            return json.dumps({
                "schema_version": "1.0",
                "prompt": "Test prompt",
                "negative_prompt": "low quality, blurry"
            })
        else:
            return json.dumps({"schema_version": "1.0", "result": "stub"})


# Global client instance
_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get or create global Gemini client instance."""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
