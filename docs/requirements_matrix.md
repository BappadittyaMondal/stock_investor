# HFOS v5.0 - Requirements Matrix

| Requirement | Status | Implementation | Evidence |
|---|---|---|---|
| Streamlit institutional UI | COMPLIANT | `main.py`, `app/pages/*` | page routing and role gate present |
| JWT + RBAC auth | COMPLIANT | `services/auth_service.py` | token, lockout, role checks implemented |
| SQLite WAL schema | COMPLIANT | `database/schema.sql`, `database/db_manager.py` | boot path initializes schema |
| 8-engine scoring flow | COMPLIANT | `engines/*`, `services/scanner_service.py`, `engines/scoring/alpha_engine.py` | composite alpha path exists |
| Portfolio service and gates | COMPLIANT | `services/portfolio_service.py`, `engines/scoring/alpha_engine.py` | sizing, exposure, and entry gates present |
| Data fetch fallback chain | COMPLIANT | `services/data_fetcher.py`, `services/screener_scraper.py` | yfinance -> nsepython -> DB cache |
| Universal screener layer | PARTIAL | `engines/screener/universal_screener.py`, `services/universal_screener.py`, `app/pages/screener_builder.py` | dynamic logic exists; some filters depend on external data |
| Full PDF filter coverage | PARTIAL | derived metrics added; unresolved items documented | `docs/FILTER_COVERAGE_AUDIT.md` |
| Deployment artifacts | COMPLIANT | `Dockerfile`, `deployment/docker-compose.yml`, `Makefile`, `.env.example` | deploy files present |
| Monitoring and audit trails | COMPLIANT | `monitoring/*`, audit tables in schema | operational reports already exist |
| Objective verification | PARTIAL | static inspection completed; live Python test runner unavailable in this shell | remaining runtime verification documented |
