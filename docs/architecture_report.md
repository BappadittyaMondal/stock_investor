# HFOS v5.0 - Architecture Report

## Layers

### Presentation
- `main.py` is the Streamlit entrypoint.
- `app/pages/*` contains page modules only.
- `api/rest_api.py` exposes a lightweight internal HTTP API.

### Services
- `services/*` contains business logic and orchestration.
- `services/scanner_service.py` runs the multi-engine scan flow.
- `services/universal_screener.py` re-exports the screener engine entrypoint.
- `services/auth_service.py` handles JWT, password hashing, RBAC, and lockout.

### Engines
- `engines/*` implements the scoring stack.
- `engines/screener/universal_screener.py` evaluates dynamic filter trees.

### Data Access
- `database/db_manager.py` centralizes SQLite access and schema bootstrap.
- `repositories/*` isolates CRUD and query logic.

### Infrastructure
- `deployment/docker-compose.yml`, `Dockerfile`, `Makefile`, and `.env.example` support local and containerized startup.
- `jobs/scheduler.py` manages background automation.

## Current Shape
- The codebase is modular and already separated by concern.
- The main remaining hardening work is verification, data coverage, and selective security tightening.
