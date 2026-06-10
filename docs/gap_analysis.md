# HFOS v5.0 - Gap Analysis

| Area | Current State | Gap | Action |
|---|---|---|---|
| UI routing | Main Streamlit app works | Missing screener builder entry | Added `screener_builder` route in `main.py` |
| Screener engine | Dynamic filter engine present | Some filter families require external data | Added derived metrics and documented dependencies |
| Auth security | JWT/RBAC in place | Blacklist lookup failed open on DB errors | Switched to fail-closed behavior |
| REST API | Functional internal API | No request body cap | Added request-size guard |
| Documentation | Many reports existed | Several were stale/overclaiming | Refreshed readiness docs |
| Runtime verification | Static inspection only in this shell | Python test runner unavailable | Documented as a remaining verification risk |

## Remaining External Data Dependencies
- Analyst forecasts
- Credit ratings
- Export percentage
- Some multi-year shareholder history
- Any filter fields not represented in `stocks`, `fundamentals`, `ohlcv_cache`, or existing activity tables
