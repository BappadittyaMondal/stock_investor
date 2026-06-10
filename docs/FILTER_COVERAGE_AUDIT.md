# HFOS v5.0 - Filter Coverage Audit

## Scope

Master filter list audited from the provided text file:

- Core Fundamentals
- Growth Metrics
- Profitability Metrics
- Annual P&L Metrics
- Quarterly Metrics
- Previous Quarter Metrics
- Previous Year Quarter Metrics
- Balance Sheet Metrics
- Historical Balance Sheet Metrics
- Cash Flow Metrics
- Valuation Metrics
- Ownership Metrics
- Efficiency Metrics
- Advanced Quality Metrics
- Technical Metrics
- Forecast Metrics
- Date Filters
- SME Filters

## Coverage Summary

- Current Coverage: approximately 80-85%
- Missing Filters Count: depends on external data availability
- Status rule: a filter is only marked supported when it can be queried or derived from existing data

## Supported immediately from current HFOS data

- ROE, ROCE, Debt to Equity, Current Ratio, Pledge, Promoter Holding
- Revenue, PAT, EBITDA, EPS, growth rates, margins
- FII/DII holding levels and recent change from stored activity
- 52-week metrics, volume metrics, DMA 50/200, return windows
- PEG, cash flow quality, CFO vs PAT, working capital days, debtor days
- Nested boolean logic and arithmetic formulas

## Partially supported

- Quarterly / annual history fields when the underlying historical rows exist
- Balance sheet fields that are not yet fully modeled in current tables
- Forecast metrics without consensus/analyst feed

## Missing / External Data Dependency

These should not be fabricated:

- Credit rating
- Export percentage
- Analyst forecast metrics
- Full multi-year shareholder history where absent
- Some deep historical balance-sheet series if not stored

## Required source mapping

| Filter family | Source table | Source field / dependency | Status |
|---|---|---|---|
| Fundamentals | `fundamentals` | `revenue_cr`, `pat_cr`, `roe_pct`, `roce_pct`, `debt_equity`, `current_ratio` | Supported |
| Shareholding | `fundamentals`, `fii_dii_activity` | `promoter_holding`, `fii_holding`, `dii_holding`, historical change | Supported/Partial |
| Technical | `ohlcv_cache` | OHLCV-derived indicators | Supported |
| Forecast | external API/manual dataset | consensus estimates | Missing |
| Credit rating | external source | credit rating feed | Missing |

