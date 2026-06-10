# HFOS v5.0 - Deployment Guide

## Local Startup
1. Copy `.env.example` to `.env`
2. Set `HFOS_JWT_SECRET`
3. Set alert and AI credentials if those features are required
4. Initialize the database through the app bootstrap path
5. Start the Streamlit app from `main.py`

## Docker Startup
- Build with the repository `Dockerfile`
- Run with `deployment/docker-compose.yml`
- Persist the SQLite volume and logs volume

## Operational Notes
- `main.py` bootstraps schema initialization and scheduler startup.
- `api/rest_api.py` runs as an internal HTTP service.
- Background jobs are scheduler-driven; ensure the process remains alive.

## Deployment Risks
- Python runtime must be available on the host/container.
- External providers may be unavailable for some filters.
- Alerts and AI features require configured secrets.
