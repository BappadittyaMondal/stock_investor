# HFOS Environment Setup

## Required Variables

These variables MUST be configured in the Railway dashboard for the application to function securely:

- `HFOS_JWT_SECRET`: A secure 32+ character string for signing JWT tokens.
- `ANTHROPIC_API_KEY`: The API key for Claude 3.5 Sonnet (powers the AI Copilot).
- `TELEGRAM_BOT_TOKEN`: The token for your Telegram alerting bot.
- `TELEGRAM_CHAT_ID`: The specific chat ID where alerts should be sent.

## Optional Variables (Future Expansion)

- `SUPABASE_URL`: The URL for your Supabase Postgres database.
- `SUPABASE_KEY`: The Service Role Key for Supabase.

> [!IMPORTANT]
> Railway injects `$PORT` automatically. Streamlit is configured via the startup command to bind to `$PORT`. You do not need to set this manually unless testing locally.
