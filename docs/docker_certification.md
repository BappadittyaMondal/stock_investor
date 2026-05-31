# HFOS v5.0 — Docker Certification

## Execution Details
**Command:** `docker compose up --build`

## Container Validation
- **`hfos-app`:** Streamlit UI boots successfully and exposes port 8501.
- **`hfos-api`:** FastAPI backend starts correctly on port 8000 using Uvicorn workers.
- **`hfos-scheduler`:** APScheduler daemon binds correctly and fires initial sync events.

## Network & Volume Validation
- Containers communicate successfully across internal Docker bridge network.
- Persistent volumes for SQLite and logs mounted successfully.

## Certification Status
**Status:** PASS
**Startup Failures:** 0
