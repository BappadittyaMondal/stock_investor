# HFOS v5.0 AI Providers

This directory contains the AI provider implementations for HFOS v5.0. 

## Pluggable Architecture

The system uses a pluggable `BaseAIProvider` interface. By default, it uses `GeminiProvider`.

### How to add a new provider

1. Create `providers/new_provider.py`
2. Extend `BaseAIProvider` from `providers/base_provider.py`.
3. Implement the `query(self, prompt: str, system_prompt: str) -> dict` method.
4. Ensure it returns a dictionary with `text`, `tokens_in`, `tokens_out`, and `cost_inr`.
5. Update `services/ai_copilot.py` to instantiate your new provider instead of `GeminiProvider`.

### Current Provider
- **Gemini**: `gemini-2.5-flash` using `google-genai`.
- Requires `GOOGLE_API_KEY` in `.env`.
