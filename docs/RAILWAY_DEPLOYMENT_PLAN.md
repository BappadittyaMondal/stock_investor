# Railway Deployment Plan

## Infrastructure Requirements
- **Target Platform:** Railway (railway.app)
- **Deployment Method:** Dockerfile (native Railway builder)
- **Database:** SQLite (persisted via Railway Volume)
- **Framework:** Streamlit (exposed on `$PORT`)

## Step-by-Step Deployment Guide

### 1. Prepare the Railway Project
1. Log into Railway and click **New Project**.
2. Select **Deploy from GitHub repo** and choose `BappadittyaMondal/stock_investor`.
3. Railway will automatically detect the `Dockerfile` and begin the build process.

### 2. Configure the Persistent Volume
*Since HFOS uses SQLite (`hfos.db`), a volume is mandatory. Otherwise, data will reset on every deployment.*
1. In the Railway dashboard, click on your deployed service.
2. Go to the **Volumes** tab.
3. Click **Add Volume**.
4. Set the Mount Path to `/app/database`. (This matches the directory where `hfos_production.db` resides).

### 3. Configure Environment Variables
1. Go to the **Variables** tab for the service.
2. Add the following required environment variables:
   - `HFOS_JWT_SECRET`: (Generate a secure random string)
   - `ANTHROPIC_API_KEY`: (Your Claude API key)
   - `TELEGRAM_BOT_TOKEN`: (Your Telegram bot token, optional)
   - `TELEGRAM_CHAT_ID`: (Your Telegram chat ID, optional)
   - `SUPABASE_URL`: (Your Supabase project URL, for future integration)
   - `SUPABASE_KEY`: (Your Supabase service role key)
   - `PORT`: `8501` (Streamlit's default port, Railway handles mapping)

### 4. Adjust Build / Start Commands
Railway uses the `Dockerfile` by default. The `Dockerfile` should contain:
```dockerfile
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```
If Railway asks for a custom start command, leave it blank to let the `Dockerfile` handle it.

### 5. Generate a Public URL
1. Go to the **Settings** tab.
2. Under **Networking**, click **Generate Domain**.
3. Railway will provide a live URL (e.g., `hfos-production.up.railway.app`).

### 6. Verification
1. Open the live URL.
2. The system should present the HFOS login page.
3. Check the Railway **Deploy Logs** to ensure there are no SQLite write-permission errors. (The volume mount at `/app/database` ensures the app has write access).
