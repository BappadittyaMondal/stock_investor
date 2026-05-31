# HFOS v5.0 — Data Lineage Report

## Lineage Strategy
Institutional audit trails require knowing exactly how an Alpha Score was generated. The `DataLineageService` automatically inserts a record into the `data_lineage` table every time the `AlphaEngine` finishes a calculation.

## What is Tracked?
- **Stock ID**: The specific ticker.
- **Target Table/Row**: Where the output was written (e.g., `scores`).
- **Source System**: "Multi-Engine" or specific overrides.
- **Transformation**: Records the exact weighting model used (e.g., `WeightVersion: v5.0` or a specific Calibrated ID).
- **Engine**: The generator (e.g., `AlphaEngine`).
- **Timestamp**: Exact microsecond of generation.

## Audit Example
If a PM asks why a stock generated a STRONG_BUY on Tuesday but disappeared on Wednesday, the data lineage trace can instantly answer:
1. Which weight version was used Tuesday vs Wednesday.
2. If data quality degraded between the runs, blocking the signal.
3. If a corporate action split the price, altering the technical indicators.
