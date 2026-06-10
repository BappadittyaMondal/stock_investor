# HFOS v5.0 MIGRATION NOTES

## Environment Variables
- **REMOVED**: `ANTHROPIC_API_KEY`
- **REMOVED**: `ANTHROPIC_MODEL`
- **ADDED**: `GOOGLE_API_KEY` (Required for AI Copilot functionality via Gemini-2.5-Flash)

## Database Schema Changes
The database schema has automatically been updated to support AI memory.
- `ai_threads` table created.
- `ai_messages` table created.

## Dependency Updates
- `anthropic` removed from `requirements.txt`.
- `google-genai==0.3.0` added to `requirements.txt`.
Run `pip install -r requirements.txt` to align the virtual environment.
