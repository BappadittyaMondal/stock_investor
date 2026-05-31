# HFOS v5.0 — Data Reliability Report

## Reliability Framework
The reliability of HFOS depends on resilient fallbacks. The engine architecture handles data failures via the `Data Health Service`.

### Fallback Matrix
| Component | Primary Source | Secondary Source | Action on Total Failure |
|-----------|----------------|------------------|-------------------------|
| Prices    | NSE API        | yfinance API     | Use DB Cache (Alert Generated) |
| Fundamentals | Screener API | TickerTape API | Return Neutral 50 score |
| Macro     | RBI/Gov Feeds  | TradingEconomics | Use Last Known Values |
| News      | Aggregated RSS | Specific Handles | Return Neutral 50 score |

### Reliability Scoring
Sources are hardcoded with a max reliability index (e.g. NSE is a 1.0, meaning it can achieve a 100/100 Data Quality Score. Free API layers are capped at 0.85). If the Quality Score of a feed drops beneath 70, the Alpha Engine algorithmically reduces output conviction to `SPECULATIVE`, preventing massive capital allocation on faulty data.

## Incident Management
- Detected anomalies (e.g. 30% price gap indicating a missed stock split) are written to `data_anomalies` and visible in the **Data Center** UI.
- The `Data Quality Monitor` runs hourly via `APScheduler` and alerts the team via Telegram if consecutive staleness is found.
