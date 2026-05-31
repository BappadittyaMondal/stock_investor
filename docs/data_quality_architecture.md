# HFOS v5.0 — Data Quality Architecture

## Overview
HFOS uses a multi-layered data quality framework designed for institutional reliability. The system assumes data is flawed until validated, isolating the Alpha Engine from bad inputs.

## Architecture

### 1. Ingestion Validation
- **Pandas Level:** Checks for negative prices, zero volume, and missing symbols during DataFrame processing.
- **Pydantic Level:** All endpoints and repositories enforce `DataValidator` models which reject corrupted schema structures.

### 2. The Data Quality Service
Located in `services/data_quality_service.py`. It computes a 0-100 score per source:
```python
quality_score = (
    completeness * 0.30 +
    freshness * 0.25 +
    consistency * 0.20 +
    accuracy * 0.15 +
    source_reliability * 0.10
)
```
- Reliability is mapped per source (e.g. NSE = 1.0, RSS = 0.70).
- Scores below 70 generate warnings.

### 3. Anomaly & Staleness Detection
Located in `services/data_health_service.py`.
- **Staleness:** Rejects OHLCV older than 1 business day, Macro older than 7 days.
- **Anomalies:** Price gaps > 30% trigger alerts and pause scoring for that ticker.

### 4. Alpha Engine Integration
The `AlphaEngine.score_batch` method intercepts data right before scoring:
- If `quality_score < 70`: Signal confidence downgraded to `SPECULATIVE`.
- If `quality_score < 50`: Signal blocked entirely (`REJECT`/`AVOID`).

### 5. Corporate Actions Engine
`CorporateActionsService` handles splits/bonuses gracefully by rewriting the `ohlcv_cache`, adjusting active portfolio entry costs and target/stops, and correcting paper trade records to prevent synthetic gap anomalies.
