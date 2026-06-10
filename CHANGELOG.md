# HFOS v5.0 CHANGELOG

## Enhancements
- **AI Engine Migration**: Completely removed Anthropic dependencies and transitioned to `gemini-2.5-flash` using a pluggable `BaseAIProvider` architecture.
- **Data Reality Update**: Cleared mock DB symbols (`SMOKE01`) and populated top-tier Indian stocks (Reliance, TCS, etc.).
- **Scanner Enrichment**: Enhanced `yfinance` data fetching to pull Market Cap, PE Ratio, and 52-Week Highs/Lows correctly during scans.
- **Dashboard Optimization**: Enabled `@st.cache_data` on expensive queries (`geo_events`, `recent_scores`, `leaderboard`) improving TTFB performance.
- **Navigation UX**: Grouped sidebar into 3 macro categories (WORKSPACE, RESEARCH, SYSTEM).
- **Admin Capability Expansion**: Added dedicated `User Management` and `Audit Logs` views.
- **AI Memory Persistence**: AI Copilot now remembers conversation history via SQLite `ai_threads` and `ai_messages`.

## Bug Fixes
- Fixed `StreamlitDuplicateElementKey` crashes in Dashboard button loops.
- Fixed `TypeError` formatting exceptions in Watchlist components for `None` market cap values.
- Intercepted all page unhandled exceptions with a global try/catch wrapper logic.
