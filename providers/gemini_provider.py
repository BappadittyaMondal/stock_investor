import logging
from .base_provider import BaseAIProvider
from config.settings import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

class GeminiProvider(BaseAIProvider):
    def __init__(self):
        if not GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not set — Gemini Provider disabled")
        self._client = None
        self.model_name = "gemini-2.5-flash"
        # Approximate costs (subject to change)
        self.cost_per_1k_in = 0.015 # INR
        self.cost_per_1k_out = 0.060 # INR

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=GOOGLE_API_KEY)
            except ImportError:
                raise RuntimeError("google-genai package not installed.")
        return self._client

    def query(self, prompt: str, system_prompt: str) -> dict:
        if not GOOGLE_API_KEY:
            return {
                "text": "⚠️ AI Copilot unavailable: GOOGLE_API_KEY not configured.",
                "tokens_in": 0, "tokens_out": 0, "cost_inr": 0.0
            }
        try:
            client = self._get_client()
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={"system_instruction": system_prompt}
            )
            text = response.text
            # Use metadata for token counting if available, else fallback
            tokens_in = response.usage_metadata.prompt_token_count if response.usage_metadata else len(prompt)//4
            tokens_out = response.usage_metadata.candidates_token_count if response.usage_metadata else len(text)//4
            cost_inr = (tokens_in / 1000 * self.cost_per_1k_in) + (tokens_out / 1000 * self.cost_per_1k_out)
            
            return {
                "text": text,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_inr": cost_inr,
                "model_name": self.model_name
            }
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise e
