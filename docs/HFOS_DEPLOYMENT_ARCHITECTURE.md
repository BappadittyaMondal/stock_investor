# HFOS Deployment Architecture

## Overview
HFOS v5.0 is a monolithic Python Streamlit application designed for institutional-grade reliability. The architecture is self-contained and avoids distributed microservices in favor of strict, well-tested Python modules operating within a single container.

## Stack
- **Frontend/UI:** Streamlit (Python)
- **Backend/Logic:** Python 3.14 (Async services, mathematical engines)
- **Database:** SQLite (WAL Mode, Thread-Local Connections, 37 Tables)
- **Containerization:** Docker (`Dockerfile`, `docker-compose.yml`)
- **Hosting Target:** Railway

## Stateful vs Stateless
- **Application Code:** Completely stateless. All engines (Alpha, Risk, Research) and services calculate on-the-fly or fetch from the database.
- **Data Persistence:** Highly stateful. The `hfos.db` SQLite file holds 37 tables, including portfolio positions, user credentials, audit logs, and cached asset prices.
- **Requirement:** Deployment requires a **persistent volume** mounted to `/app/database` to ensure `hfos.db`, `hfos.db-wal`, and `hfos.db-shm` survive container restarts.

## Dependency Flow
1. User interacts via Streamlit UI (`main.py` -> `app/pages/`).
2. UI calls `services/` for business logic.
3. `services/` invoke `engines/` for quantitative analysis or `repositories/` for DB access.
4. `repositories/` use `db_manager.py` (thread-local SQLite connections) to read/write state.
5. Background jobs (`scheduler.py`) run periodically within the same container to update asset prices and perform data freshness checks.
