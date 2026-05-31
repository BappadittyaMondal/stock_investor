# HFOS v5.0 — DEFECT REMEDIATION LOG
**Audit Date:** 2026-05-31

---

## DEFECT #1 — RiskEngine Missing Market Cap Scoring

| Field | Value |
|-------|-------|
| Severity | HIGH |
| File | `engines/risk/risk_engine.py` |
| Root Cause | `_liquidity_score()` method did not exist. `market_cap_cr` and `avg_daily_vol` were never consumed by any scoring component. Small-cap and large-cap stocks received identical risk scores for liquidity risk. |
| Impact | Alpha signals incorrectly treated micro-caps as equivalent risk to Nifty-50 large-caps. Position sizing and gate logic was miscalibrated for small-cap universe. |
| Test | `test_low_market_cap_increases_risk` was FAILING |

**Fix Applied:** Added `_liquidity_score(d: dict)` method. Weights rebalanced: debt 20%→15%, liquidity 0%→5%.

---

## DEFECT #2 — AlphaEngine Validates Non-Score Fields

| Field | Value |
|-------|-------|
| Severity | HIGH |
| File | `engines/scoring/alpha_engine.py:86` |
| Root Cause | `calculate()` iterated `for key in scores` and called `DataValidator.validate_score()` on ALL keys including `avg_daily_vol`, `asm_flag`, `pledge_pct`. These are gate-check fields with values like `5_000_000` — far outside [0,100]. |
| Impact | `calculate()` raised `ValueError` for any stock dict that included gate-check fields alongside score fields. The engine could not process real production payloads. |
| Test | `test_calculate_returns_float` was passing only because test fixtures didn't include gate fields |

**Fix Applied:** Changed loop to `{k for k in scores if k.endswith("_score")}` — only `_score` suffixed keys are validated.

---

## DEFECT #3 — Research Engines Return Randomized Output

| Field | Value |
|-------|-------|
| Severity | CRITICAL |
| Files | `engines/backtest_engine.py`, `engines/walkforward_engine.py`, `engines/monte_carlo_engine.py`, `engines/benchmark_engine.py`, `engines/factor_analysis_engine.py` |
| Root Cause | All 5 engines returned `np.random.uniform()` values. No actual mathematical computation occurred. Every "result" was a fabricated number. |
| Impact | The Research Lab UI was displaying entirely fake statistics. Any investment decision informed by these numbers would be based on random data. No strategy could actually be validated. |

**Fix Applied:**
- `BacktestEngine`: Real CAGR, Sharpe, Sortino, Max Drawdown from price series
- `WalkForwardEngine`: Real rolling OOS Sharpe decay across configurable windows
- `MonteCarloEngine`: Real bootstrap resampling with deterministic seed=42
- `BenchmarkEngine`: Real beta (covariance regression), Jensen's alpha, tracking error, info ratio
- `FactorAnalysisEngine`: Real contribution % from actual input scores

---

## DEFECT #4 — Docker Engine Not Installed (Environment)

| Field | Value |
|-------|-------|
| Severity | BLOCKING (environment, not code) |
| Impact | Cannot complete Phase 13 Docker Validation on this machine |
| Remediation | Install Docker Desktop; run `docker build . && docker compose up` |

---

## SUMMARY
| # | Severity | Status |
|---|----------|--------|
| 1 | HIGH | ✅ FIXED |
| 2 | HIGH | ✅ FIXED |
| 3 | CRITICAL | ✅ FIXED |
| 4 | ENV | ⚠️ REQUIRES DOCKER INSTALL |
