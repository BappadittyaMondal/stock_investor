# HFOS v5.0 - Screener Filter Coverage Report

This report tracks the universal screener layer added from the PDF query set.

## Supported by the new universal engine

- `ROE`
- `ROCE`
- `Debt to equity`
- `Current ratio`
- `Promoter holding`
- `FII holding change`
- `DII holding change`
- `Promoter holding change`
- `52 week index`
- `Volume expansion`
- `PEG ratio`
- `Cash flow quality`
- `CFO vs PAT`
- `Asset turnover ratio`
- `Working capital days`
- `Debtor days`

## Filter model

- Operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `BETWEEN`, `IN`, `NOT IN`
- Arithmetic expressions: `+`, `-`, `*`, `/`
- Logical groups: nested `AND` / `OR`
- Execution: row-level evaluation over active stocks

## Notes

- The engine is dynamic and template-driven.
- Fields that depend on absent source data return `null` and are marked unsupported for that specific stock.
- Existing production tables are reused; no destructive schema changes were introduced.
