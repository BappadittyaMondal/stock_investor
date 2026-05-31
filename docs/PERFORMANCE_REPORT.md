# HFOS v5.0 — PERFORMANCE BENCHMARK REPORT (REAL)
**Audit Date:** 2026-05-31  
**Command:** `py scripts/validate_and_bench.py`  
**Method:** 100 iterations per benchmark, average + p95 reported

---

## RAW TERMINAL OUTPUT (verbatim)
```
=== PHASE 14: PERFORMANCE BENCHMARK ===

Database Queries (SQLite):
  SELECT * FROM stocks                           avg=0.027ms  p95=0.013ms
  PRAGMA integrity_check                         avg=0.623ms  p95=1.248ms

Alpha Engine:
  AlphaEngine.calculate()                        avg=0.022ms  p95=0.034ms
  AlphaEngine.classify(75.0)                     avg=0.001ms  p95=0.001ms

Data Validation:
  DataValidator.validate_ohlcv(60 rows)          avg=4.824ms  p95=7.593ms

Research Engines:
  BacktestEngine.run(252 prices)                 avg=0.219ms  p95=0.481ms
  MonteCarloEngine.run(100 sims)                 avg=1.460ms  p95=3.382ms

[OK] Validation and benchmark complete
```

---

## PERFORMANCE vs TARGETS

| Component | Measured (avg) | Target | Status |
|-----------|---------------|--------|--------|
| DB SELECT query | 0.027ms | < 10ms | ✅ PASS (370x under target) |
| Alpha Engine calculate | 0.022ms | < 100ms | ✅ PASS (4500x under target) |
| Alpha Engine classify | 0.001ms | < 100ms | ✅ PASS |
| BacktestEngine (252 days) | 0.219ms | < 1000ms | ✅ PASS |
| Monte Carlo (100 sims) | 1.460ms | < 1000ms | ✅ PASS |
| DataValidator OHLCV | 4.824ms | < 50ms | ✅ PASS |

> [!NOTE]
> Dashboard and Scanner page load times cannot be benchmarked without a running browser session.
> The browser subagent quota was exhausted during this audit. The Streamlit server IS confirmed running on port 8501.

## VERDICT
```
PHASE 14 PERFORMANCE: PASS
All measurable components are well within institutional latency targets.
AlphaEngine processes one stock in 0.022ms — capable of scoring 45,000 stocks/second.
```
