# HFOS v5.0 — Deployment Guide

## 1. Environment Preparation
Ensure the host has Docker and Docker Compose installed (or Python 3.11+ for bare-metal).

```bash
cp .env.example .env
```
Edit `.env` and configure:
- `HFOS_JWT_SECRET` (Must be cryptographically secure, >= 32 chars)
- `ANTHROPIC_API_KEY` (Required for AI Copilot)
- `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID` (Required for alerts)

## 2. Docker Deployment (Recommended)
```bash
make build
make docker-up
```
The application will be accessible at `http://localhost:8501`.
Data and logs are persisted in named Docker volumes (`hfos_data`, `hfos_logs`).

## 3. Bare-Metal Deployment
If running without Docker:
```bash
pip install -r requirements.txt
make init-db
make run
```

## 4. Post-Deployment Steps
1. Navigate to `http://localhost:8501`.
2. Login (create admin user via DB or wait for first-run prompt if configured).
3. Navigate to **Settings**.
4. Upload `stocks.csv` to populate the `stocks` universe table.
5. Navigate to **Universe Scanner** and execute a manual scan to prime the system caches.

## 5. Maintenance
- Logs rotate automatically at 10MB and are retained for 30 days.
- Database runs `VACUUM` nightly via the scheduler.
- To completely reset the cache, run `make clean` and delete `hfos_production.db`.
