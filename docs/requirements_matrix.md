# HFOS v5.0 — Requirements Matrix

| Requirement | Category | Status | Notes |
|-------------|----------|--------|-------|
| 8 Intelligence Engines | Core | Implemented | Fundamental, Technical, Risk, Sector, News, Macro, Geo, Policy |
| Alpha Scoring Engine | Core | Implemented | Weighted scoring on 0-100 scale with inverted risk |
| Hard Risk Gates | Core | Implemented | ASM/GSM, Pledge > 40%, Market Cap < 200Cr filters |
| Walk-Forward Calibration | Advanced | Implemented | Sharpe-ratio optimized grid search across paper trades |
| Paper Trading Simulation | Advanced | Implemented | Auto open/close tracking for backtesting validation |
| Streamlit SPA Interface | UI | Implemented | Premium dark theme, multi-page routing |
| JWT Role-Based Auth | Security | Implemented | PBKDF2 hashing, lockout logic, token blacklist |
| SQLite WAL Database | Infrastructure| Implemented | 22 tables, thread-local connection pooling |
| Claude AI Copilot | Intelligence | Implemented | Cost-tracked portfolio review and Q&A |
| Alert Engine | Notifications | Implemented | Telegram / Email with automatic retry |
| Data Validation Layer | Reliability | Implemented | Pydantic v2 schemas and pandas OHLCV checks |
| APScheduler Automation | DevOps | Implemented | Pre/post market scans, weekend reviews, DB maintenance |
