# HFOS v5.0 — Architecture Report

## High-Level Architecture
The HFOS v5.0 platform utilizes a modular, layered architecture designed for separation of concerns, strict data validation, and fault tolerance.

### 1. Presentation Layer (Streamlit & API)
- `main.py` serves as the Streamlit SPA entry point, handling JWT auth state and page routing.
- `app/pages/` contains isolated UI modules (Dashboard, Scanner, Portfolio, etc.).
- `api/rest_api.py` exposes programmatic access for webhooks and external integrations.
- *Rule:* No business logic or raw SQL exists in this layer.

### 2. Service Layer
- Contains orchestrators like `ScannerService`, `PortfolioService`, and `AlertService`.
- Responsible for combining data from repositories and feeding it into intelligence engines.
- `DataFetcher` manages the multi-source fallback chain (YFinance → NSEPython → DB Cache).

### 3. Intelligence Engines
- The 8 core engines (`fundamental`, `technical`, `risk`, `sector`, `news`, `macro`, `geo`, `policy`) independently score aspects of a stock on a 0-100 scale.
- `AlphaEngine` aggregates these using dynamically calibrated weights.
- `CalibrationEngine` runs statistical walk-forward optimization.
- `PaperTradingEngine` simulates trades for performance validation.

### 4. Data Access Layer
- Repositories (`StockRepository`, `PortfolioRepository`, etc.) encapsulate all database access.
- Pydantic v2 schemas (`schemas/validators.py`) enforce strict type validation at the IO boundaries.

### 5. Infrastructure Layer
- SQLite database configured for high concurrency (WAL mode, shared cache, thread-local connections).
- APScheduler manages background cron jobs.
- Docker orchestrates the unified application stack.
