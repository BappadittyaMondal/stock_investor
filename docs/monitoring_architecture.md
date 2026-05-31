# HFOS v5.0 — Monitoring & Observability Architecture

## Overview
HFOS uses an active self-monitoring architecture to prevent silent failures and provide institutional observability. The `monitoring/` module centralizes metrics collection, telemetry tracking, and health checks.

## Key Components

### 1. Health Service (`monitoring/health_service.py`)
Executes real-time latency and connectivity checks against:
- Database (SQLite/Postgres)
- Scheduler (APScheduler)
- External APIs (Telegram, AI Copilot quotas)
- Data feeds

### 2. Telemetry Service (`monitoring/telemetry_service.py`)
Tracks the duration and success state of critical system actions. By wrapping `AlphaEngine.score_batch()` and database operations in telemetry logs, HFOS guarantees performance monitoring.
**Target Metrics:**
- Dashboard Load: < 2s
- Scanner Load: < 1s
- Portfolio Load: < 1s
- Alpha Calculation: < 100ms

### 3. Alert Router (`monitoring/alert_router.py`)
Centralizes all outbound system alerts, sorting them by priority:
- **P1 (CRITICAL):** Database down, core feed failure.
- **P2 (HIGH):** Data anomaly detected, AI budget depleted.
- **P3 (MEDIUM):** Portfolio limit breached.
- **P4 (LOW):** Execution successful.

### 4. Database Integration
New tables introduced in `schema.sql`:
- `system_metrics`: High cardinality time-series metrics.
- `telemetry_logs`: Duration and status of actions.
- `system_errors`: Service-level error tracking and recovery states.
