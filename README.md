# HFOS v5.0 — Hedge-Fund Operating System

> **Institutional-grade equity research and portfolio management platform for Indian markets (NSE/BSE)**

---

## ⚠️ Legal Disclaimer

**Not SEBI Registered | Private Research Only | Not Investment Advice**
This system is built for private, institutional-style research. All signals and scores are informational. Past performance of paper trades does not guarantee future results.

---

## Architecture Overview

```
main.py                 ← Streamlit entry-point (auth, scheduler boot, routing)
├── app/pages/          ← 11 Streamlit UI pages (dashboard, scanner, portfolio …)
├── engines/            ← 8 intelligence engines + calibration + paper trading
│   ├── scoring/        ← AlphaEngine (8-engine composite, 0-100 scale)
│   ├── fundamental/    ← ROE, ROCE, growth, valuation, quality scoring
│   ├── technical/      ← TA scoring via pandas-ta (trend, momentum, volume)
│   ├── risk/           ← ASM/GSM flags, pledge, debt, governance
│   ├── sector/         ← Sector rotation, tailwinds, policy alignment
│   ├── news/           ← RSS sentiment analysis (PIB, RBI, SEBI feeds)
│   ├── macro/          ← RBI repo rate, inflation, FII flows, GDP
│   ├── geo/            ← Geopolitical event risk scoring
│   ├── policy/         ← PLI and government scheme beneficiary mapping
│   ├── paper_trading/  ← Virtual trade lifecycle for calibration data
│   └── calibration/    ← Walk-forward weight optimizer (Sharpe-based)
├── services/           ← Business logic layer
│   ├── data_fetcher.py     ← yfinance → nsepython → DB cache fallback
│   ├── screener_scraper.py ← Screener.in fundamentals scraper
│   ├── scanner_service.py  ← Full universe scan orchestrator
│   ├── portfolio_service.py← Kelly sizing, XIRR, Indian tax (STCG/LTCG)
│   ├── alert_service.py    ← Telegram + Email alerts with retry
│   ├── auth_service.py     ← JWT + PBKDF2 + RBAC + lockout (OWASP)
│   └── ai_copilot.py       ← Claude AI research assistant (cost-tracked)
├── repositories/       ← Data access layer (no SQL in services/UI)
├── database/           ← SQLite WAL, 22-table schema, migrations
├── jobs/scheduler.py   ← APScheduler (7 jobs, IST-aware)
├── tests/              ← pytest: unit + integration + E2E (90%+ target)
└── deployment/         ← Docker + docker-compose
```

---

## Quick Start

### 1. Prerequisites
```
Python 3.11+
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env — set HFOS_JWT_SECRET at minimum
```

### 3. Initialize Database & Launch
```bash
make init-db   # Creates all 22 tables
make run       # Streamlit on http://localhost:8501
```

### 4. Load Stock Universe
- Go to **Settings** page → Upload `stocks.csv`
- Required columns: `symbol`, `name`
- Optional: `exchange`, `sector`, `market_cap_cr`, `isin`

### 5. Run First Scan
- Go to **Universe Scanner** → click **▶ Run Scan**
- Scores are persisted; signals trigger Telegram alerts (if configured)

---

## Scheduler Jobs (Auto-running)

| Job | Time (IST) | Description |
|-----|-----------|-------------|
| Pre-market scan | Mon–Fri 08:30 | Top-50 watchlist refresh |
| Post-market scan | Mon–Fri 16:00 | Full universe score + signals |
| Paper trade close | Mon–Fri 16:30 | Evaluate open paper trades vs LTP |
| Alert retry | Every 30 min | Retry failed Telegram/email alerts |
| Freshness check | Every hour | Alert if data source RED |
| DB maintenance | Daily 00:00 | Purge old tokens/news, VACUUM |
| Weekend research | Saturday 10:00 | AI portfolio review via Claude |

---

## Engine Weights (Default, v5.0)

| Engine | Weight | Notes |
|--------|--------|-------|
| Fundamental | 25% | ROE, ROCE, growth, valuation |
| Technical | 20% | TA via pandas-ta |
| Sector | 15% | Tailwind, rotation |
| Risk | 12% | **Inverted** — higher risk = lower alpha |
| Policy | 10% | PLI, scheme beneficiaries |
| News | 10% | RSS sentiment |
| Macro | 8% | RBI, FII, GDP |
| Geo | 0%* | Activated after calibration |

> Weights auto-calibrate via **Walk-Forward Calibration** (Admin page). Approved weights load on next restart.

---

## Signal Classification

| Alpha Score | Signal | Confidence |
|-------------|--------|------------|
| ≥ 90 | STRONG_BUY | INSTITUTIONAL |
| ≥ 80 | BUY | HIGH_CONVICTION |
| ≥ 70 | ACCUMULATE | WATCHLIST |
| ≥ 50 | WATCH | SPECULATIVE |
| < 50 | REJECT | AVOID |

---

## Portfolio Hard Gates (Pre-entry checks)

All must pass before any position entry:
- ❌ ASM / GSM flag = immediate exclusion
- ❌ Pledge > 40% = excluded
- ❌ Alpha < 75 = excluded
- ❌ Sector exposure ≥ 25% = capacity full
- ❌ Avg daily volume < 5L = illiquid
- ❌ Market cap < ₹200 Cr = micro-cap exclusion

---

## Docker Deployment

```bash
make build        # Build image
make docker-up    # Start container (background)
make docker-down  # Stop container
```

Data persists in named Docker volumes: `hfos_data`, `hfos_logs`.

---

## Testing

```bash
make test                              # All tests
python -m pytest tests/unit/           # Unit only
python -m pytest tests/integration/   # Integration (real SQLite)
python -m pytest tests/e2e/           # E2E smoke pipeline
```

Target: **≥ 90% coverage** on engines and services.

---

## Roles & Permissions

| Role | Access |
|------|--------|
| ADMIN | Full access including user management, calibration approval |
| PORTFOLIO_MANAGER | Portfolio, scanner, alerts, calibration run |
| RESEARCHER | Research read/write, scanner, news |
| VIEWER | Read-only on portfolio and stocks |

---

## File Counts (Production Build)

| Category | Files |
|----------|-------|
| Engines | 11 modules |
| Services | 7 modules |
| UI Pages | 11 pages |
| Repositories | 3 modules |
| Tests | 6 test files (80+ test cases) |
| DB Schema | 22 tables |
| Scheduler Jobs | 7 jobs |

---

*HFOS v5.0 — Built for institutional-style private research on Indian equity markets.*
