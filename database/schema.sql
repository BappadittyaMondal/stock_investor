-- =============================================================================
-- HFOS v5.0 — Complete Database Schema
-- Supports SQLite (primary) + PostgreSQL migration path
-- =============================================================================
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;

-- =============================================================================
-- I. STOCKS — Master security universe
-- =============================================================================
CREATE TABLE IF NOT EXISTS stocks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    name            TEXT    NOT NULL,
    exchange        TEXT    NOT NULL DEFAULT 'NSE'
                    CHECK(exchange IN ('NSE','BSE','BOTH')),
    sector          TEXT,
    industry        TEXT,
    market_cap_cr   REAL    CHECK(market_cap_cr >= 0),
    isin            TEXT    UNIQUE,
    face_value      REAL    DEFAULT 10.0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    asm_flag        INTEGER NOT NULL DEFAULT 0,
    gsm_flag        INTEGER NOT NULL DEFAULT 0,
    pledge_pct      REAL    DEFAULT 0.0 CHECK(pledge_pct BETWEEN 0 AND 100),
    avg_daily_vol   INTEGER DEFAULT 0,
    nse_series      TEXT    DEFAULT 'EQ',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_stocks_symbol   ON stocks(symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_sector   ON stocks(sector);
CREATE INDEX IF NOT EXISTS idx_stocks_exchange ON stocks(exchange, is_active);
CREATE INDEX IF NOT EXISTS idx_stocks_asm      ON stocks(asm_flag, gsm_flag);

-- =============================================================================
-- II. OHLCV CACHE
-- =============================================================================
CREATE TABLE IF NOT EXISTS ohlcv_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id    INTEGER NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    date        TEXT    NOT NULL,
    open        REAL    NOT NULL CHECK(open > 0),
    high        REAL    NOT NULL CHECK(high > 0),
    low         REAL    NOT NULL CHECK(low > 0),
    close       REAL    NOT NULL CHECK(close > 0),
    volume      INTEGER NOT NULL DEFAULT 0,
    UNIQUE(stock_id, date)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_stock_date ON ohlcv_cache(stock_id, date DESC);

-- =============================================================================
-- III. FUNDAMENTAL DATA
-- =============================================================================
CREATE TABLE IF NOT EXISTS fundamentals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    report_date     TEXT    NOT NULL,
    period_type     TEXT    NOT NULL DEFAULT 'QUARTERLY'
                    CHECK(period_type IN ('QUARTERLY','ANNUAL','TTM')),
    revenue_cr      REAL,
    ebitda_cr       REAL,
    pat_cr          REAL,
    eps             REAL,
    pe_ratio        REAL,
    pb_ratio        REAL,
    roe_pct         REAL,
    roce_pct        REAL,
    debt_equity     REAL,
    current_ratio   REAL,
    promoter_holding REAL CHECK(promoter_holding BETWEEN 0 AND 100),
    fii_holding     REAL CHECK(fii_holding BETWEEN 0 AND 100),
    dii_holding     REAL CHECK(dii_holding BETWEEN 0 AND 100),
    pledged_pct     REAL DEFAULT 0.0 CHECK(pledged_pct BETWEEN 0 AND 100),
    dividend_yield  REAL DEFAULT 0.0,
    revenue_growth_yoy REAL,
    pat_growth_yoy  REAL,
    operating_cf    REAL,
    fcf_cr          REAL,
    source          TEXT    DEFAULT 'screener',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(stock_id, report_date, period_type)
);
CREATE INDEX IF NOT EXISTS idx_fund_stock_date ON fundamentals(stock_id, report_date DESC);

-- =============================================================================
-- IV. SCORES — All 8 engine outputs
-- =============================================================================
CREATE TABLE IF NOT EXISTS scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id            INTEGER NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    scored_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    fundamental_score   REAL    NOT NULL CHECK(fundamental_score BETWEEN 0 AND 100),
    technical_score     REAL    NOT NULL CHECK(technical_score BETWEEN 0 AND 100),
    sector_score        REAL    NOT NULL CHECK(sector_score BETWEEN 0 AND 100),
    risk_score          REAL    NOT NULL CHECK(risk_score BETWEEN 0 AND 100),
    policy_score        REAL    NOT NULL CHECK(policy_score BETWEEN 0 AND 100),
    news_score          REAL    NOT NULL CHECK(news_score BETWEEN 0 AND 100),
    macro_score         REAL    NOT NULL CHECK(macro_score BETWEEN 0 AND 100),
    geo_score           REAL    NOT NULL DEFAULT 50.0 CHECK(geo_score BETWEEN 0 AND 100),
    alpha_score         REAL    NOT NULL CHECK(alpha_score BETWEEN 0 AND 100),
    signal              TEXT    NOT NULL CHECK(signal IN ('STRONG_BUY','BUY','ACCUMULATE','WATCH','REJECT')),
    confidence          TEXT    NOT NULL CHECK(confidence IN ('INSTITUTIONAL','HIGH_CONVICTION','WATCHLIST','SPECULATIVE','AVOID')),
    weight_version      TEXT    NOT NULL DEFAULT 'v5.0'
);
CREATE INDEX IF NOT EXISTS idx_scores_stock    ON scores(stock_id, scored_at DESC);
CREATE INDEX IF NOT EXISTS idx_scores_alpha    ON scores(alpha_score DESC, scored_at DESC);
CREATE INDEX IF NOT EXISTS idx_scores_signal   ON scores(signal, scored_at DESC);

-- =============================================================================
-- V. CALIBRATION RUNS
-- =============================================================================
CREATE TABLE IF NOT EXISTS calibration_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date        TEXT    NOT NULL DEFAULT (datetime('now')),
    positions_tested INTEGER NOT NULL,
    positions_used  INTEGER NOT NULL,
    fw_fundamental  REAL    NOT NULL,
    fw_technical    REAL    NOT NULL,
    fw_risk         REAL    NOT NULL,
    fw_sector       REAL    NOT NULL,
    fw_policy       REAL    NOT NULL,
    fw_news         REAL    NOT NULL,
    fw_macro        REAL    NOT NULL,
    fw_geo          REAL    NOT NULL DEFAULT 0.0,
    sharpe_train    REAL,
    sharpe_test     REAL,
    max_dd_test     REAL,
    status          TEXT    NOT NULL DEFAULT 'DRAFT'
                    CHECK(status IN ('DRAFT','APPROVED','REJECTED')),
    approved_by     INTEGER REFERENCES users(id),
    notes           TEXT
);

-- =============================================================================
-- VI. PORTFOLIO
-- =============================================================================
CREATE TABLE IF NOT EXISTS portfolio (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER NOT NULL REFERENCES stocks(id),
    quantity        INTEGER NOT NULL CHECK(quantity > 0),
    avg_cost        REAL    NOT NULL CHECK(avg_cost > 0),
    entry_date      TEXT    NOT NULL,
    stop_loss       REAL    CHECK(stop_loss > 0),
    target_price    REAL    CHECK(target_price > 0),
    position_size   REAL    CHECK(position_size BETWEEN 0 AND 100),
    tier            TEXT    CHECK(tier IN ('TIER1','TIER2','TIER3','TIER4')),
    strategy        TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    exit_date       TEXT,
    exit_price      REAL,
    exit_reason     TEXT,
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_portfolio_stock  ON portfolio(stock_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_active ON portfolio(is_active);

-- =============================================================================
-- VII. TRANSACTIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    INTEGER REFERENCES portfolio(id),
    stock_id        INTEGER NOT NULL REFERENCES stocks(id),
    txn_type        TEXT    NOT NULL CHECK(txn_type IN ('BUY','SELL','DIVIDEND','SPLIT','BONUS')),
    quantity        INTEGER NOT NULL,
    price           REAL    NOT NULL CHECK(price > 0),
    brokerage       REAL    DEFAULT 0.0,
    stt             REAL    DEFAULT 0.0,
    exchange_charges REAL   DEFAULT 0.0,
    gst             REAL    DEFAULT 0.0,
    net_amount      REAL    NOT NULL,
    txn_date        TEXT    NOT NULL,
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_txn_stock   ON transactions(stock_id, txn_date DESC);
CREATE INDEX IF NOT EXISTS idx_txn_date    ON transactions(txn_date DESC);

-- =============================================================================
-- VIII. FACTOR EXPOSURE
-- =============================================================================
CREATE TABLE IF NOT EXISTS factor_exposure (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date       TEXT    NOT NULL DEFAULT (datetime('now')),
    factor_momentum     REAL    NOT NULL DEFAULT 0.0,
    factor_value        REAL    NOT NULL DEFAULT 0.0,
    factor_quality      REAL    NOT NULL DEFAULT 0.0,
    factor_size         REAL    NOT NULL DEFAULT 0.0,
    sector_max_pct      REAL    NOT NULL DEFAULT 0.0,
    top_sector          TEXT,
    hhi_concentration   REAL    CHECK(hhi_concentration BETWEEN 0 AND 1),
    portfolio_beta      REAL,
    portfolio_volatility REAL
);

-- =============================================================================
-- IX. GEO-POLITICAL EVENTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS geo_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date      TEXT    NOT NULL DEFAULT (datetime('now')),
    event_type      TEXT    NOT NULL CHECK(event_type IN (
                        'BORDER_TENSION','TRADE_WAR','SANCTIONS',
                        'OIL_SHOCK','CURRENCY_CRISIS','ELECTION',
                        'RBI_POLICY','SEBI_REGULATION','OTHER')),
    title           TEXT    NOT NULL,
    summary         TEXT,
    affected_sectors TEXT,
    severity        TEXT    NOT NULL DEFAULT 'MEDIUM'
                    CHECK(severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    source_url      TEXT,
    processed       INTEGER NOT NULL DEFAULT 0,
    score_impact    REAL    DEFAULT 0.0
);
CREATE INDEX IF NOT EXISTS idx_geo_date ON geo_events(event_date DESC);

-- =============================================================================
-- X. NEWS & SENTIMENT
-- =============================================================================
CREATE TABLE IF NOT EXISTS news_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id),
    source          TEXT    NOT NULL,
    title           TEXT    NOT NULL,
    url             TEXT,
    published_at    TEXT    NOT NULL,
    sentiment       TEXT    CHECK(sentiment IN ('POSITIVE','NEUTRAL','NEGATIVE')),
    sentiment_score REAL    CHECK(sentiment_score BETWEEN -1 AND 1),
    is_material     INTEGER DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_news_stock ON news_items(stock_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_date  ON news_items(published_at DESC);

-- =============================================================================
-- XI. EARNINGS CALENDAR
-- =============================================================================
CREATE TABLE IF NOT EXISTS earnings_calendar (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER NOT NULL REFERENCES stocks(id),
    earnings_date   TEXT    NOT NULL,
    period          TEXT    NOT NULL,
    eps_estimate    REAL,
    eps_actual      REAL,
    revenue_estimate_cr REAL,
    revenue_actual_cr   REAL,
    surprise_pct    REAL,
    concall_date    TEXT,
    concall_notes   TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_earnings_date  ON earnings_calendar(earnings_date);
CREATE INDEX IF NOT EXISTS idx_earnings_stock ON earnings_calendar(stock_id);

-- =============================================================================
-- XII. FII/DII ACTIVITY
-- =============================================================================
CREATE TABLE IF NOT EXISTS fii_dii_activity (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_date   TEXT    NOT NULL,
    fii_buy_cr      REAL    DEFAULT 0.0,
    fii_sell_cr     REAL    DEFAULT 0.0,
    fii_net_cr      REAL    DEFAULT 0.0,
    dii_buy_cr      REAL    DEFAULT 0.0,
    dii_sell_cr     REAL    DEFAULT 0.0,
    dii_net_cr      REAL    DEFAULT 0.0,
    source          TEXT    DEFAULT 'NSE',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(activity_date)
);
CREATE INDEX IF NOT EXISTS idx_fii_date ON fii_dii_activity(activity_date DESC);

-- =============================================================================
-- XIII. BULK/BLOCK DEALS
-- =============================================================================
CREATE TABLE IF NOT EXISTS bulk_deals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id),
    deal_date       TEXT    NOT NULL,
    deal_type       TEXT    NOT NULL CHECK(deal_type IN ('BULK','BLOCK')),
    client_name     TEXT,
    txn_type        TEXT    CHECK(txn_type IN ('BUY','SELL')),
    quantity        INTEGER,
    price           REAL,
    exchange        TEXT    DEFAULT 'NSE',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_bulk_stock ON bulk_deals(stock_id, deal_date DESC);

-- =============================================================================
-- XIV. WATCHLISTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS watchlists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    stock_id    INTEGER NOT NULL REFERENCES stocks(id),
    tier        TEXT    NOT NULL CHECK(tier IN (
                    'HIGH_CONVICTION','EMERGING_LEADERS',
                    'POLICY_BENEFICIARIES','SPECULATIVE',
                    'TURNAROUND')),
    added_by    INTEGER REFERENCES users(id),
    notes       TEXT,
    added_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(name, stock_id)
);
CREATE INDEX IF NOT EXISTS idx_watchlist_tier ON watchlists(tier);

-- =============================================================================
-- XV. ALERTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type      TEXT    NOT NULL,
    stock_id        INTEGER REFERENCES stocks(id),
    message         TEXT    NOT NULL,
    priority        TEXT    NOT NULL DEFAULT 'MEDIUM'
                    CHECK(priority IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    delivery_method TEXT    NOT NULL DEFAULT 'TELEGRAM'
                    CHECK(delivery_method IN ('TELEGRAM','EMAIL','BOTH','LOG')),
    sent            INTEGER NOT NULL DEFAULT 0,
    delivered_at    TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_alerts_sent     ON alerts(sent, created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_priority ON alerts(priority, sent);

-- =============================================================================
-- XVI. USERS
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    email           TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash   TEXT    NOT NULL,
    role            TEXT    NOT NULL DEFAULT 'VIEWER'
                    CHECK(role IN ('ADMIN','RESEARCHER','PORTFOLIO_MANAGER','VIEWER')),
    is_active       INTEGER NOT NULL DEFAULT 1,
    failed_logins   INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,
    mfa_secret      TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    last_login      TEXT
);

-- =============================================================================
-- XVII. TOKEN BLACKLIST (JWT logout/revocation)
-- =============================================================================
CREATE TABLE IF NOT EXISTS token_blacklist (
    jti         TEXT PRIMARY KEY,
    expires_at  TEXT NOT NULL,
    revoked_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_blacklist_exp ON token_blacklist(expires_at);

-- =============================================================================
-- XVIII. AUDIT LOG
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id),
    action      TEXT    NOT NULL,
    resource    TEXT,
    detail      TEXT,
    ip_address  TEXT,
    user_agent  TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at);

-- =============================================================================
-- XIX. DATA FRESHNESS MONITOR
-- =============================================================================
CREATE TABLE IF NOT EXISTS data_freshness (
    source              TEXT    PRIMARY KEY,
    last_updated        TEXT    NOT NULL,
    next_scheduled      TEXT,
    status              TEXT    NOT NULL DEFAULT 'GREEN'
                        CHECK(status IN ('GREEN','AMBER','RED')),
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT
);

-- =============================================================================
-- XX. API COSTS TRACKER
-- =============================================================================
CREATE TABLE IF NOT EXISTS api_costs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    model       TEXT    NOT NULL,
    task        TEXT    NOT NULL,
    tokens_in   INTEGER NOT NULL DEFAULT 0,
    tokens_out  INTEGER NOT NULL DEFAULT 0,
    cost_inr    REAL    NOT NULL DEFAULT 0.0,
    cached      INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_costs_date  ON api_costs(created_at);
CREATE INDEX IF NOT EXISTS idx_costs_model ON api_costs(model, created_at);

-- =============================================================================
-- XXI. SECTOR METADATA
-- =============================================================================
CREATE TABLE IF NOT EXISTS sector_metadata (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_name     TEXT    NOT NULL UNIQUE,
    theme           TEXT,
    pe_median       REAL,
    pb_median       REAL,
    roe_median      REAL,
    policy_tailwind INTEGER NOT NULL DEFAULT 0,
    policy_notes    TEXT,
    macro_sensitivity REAL  DEFAULT 0.5,
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- =============================================================================
-- XXII. PAPER TRADING LOG
-- =============================================================================
CREATE TABLE IF NOT EXISTS paper_trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER NOT NULL REFERENCES stocks(id),
    alpha_score     REAL    NOT NULL,
    signal          TEXT    NOT NULL,
    entry_price     REAL    NOT NULL,
    stop_loss       REAL,
    target_price    REAL,
    exit_price      REAL,
    entry_date      TEXT    NOT NULL,
    exit_date       TEXT,
    pnl_pct         REAL,
    outcome         TEXT    CHECK(outcome IN ('WIN','LOSS','OPEN','STOPPED')),
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_paper_date ON paper_trades(entry_date DESC);

-- =============================================================================
-- XXIII. DATA QUALITY METRICS
-- =============================================================================
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT    NOT NULL,
    quality_score   REAL    NOT NULL CHECK(quality_score BETWEEN 0 AND 100),
    completeness    REAL    NOT NULL CHECK(completeness BETWEEN 0 AND 1),
    freshness       REAL    NOT NULL CHECK(freshness BETWEEN 0 AND 1),
    consistency     REAL    NOT NULL CHECK(consistency BETWEEN 0 AND 1),
    accuracy        REAL    NOT NULL CHECK(accuracy BETWEEN 0 AND 1),
    reliability     REAL    NOT NULL CHECK(reliability BETWEEN 0 AND 1),
    evaluated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_dqm_source ON data_quality_metrics(source, evaluated_at DESC);

-- =============================================================================
-- XXIV. DATA LINEAGE
-- =============================================================================
CREATE TABLE IF NOT EXISTS data_lineage (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id),
    target_table    TEXT    NOT NULL,
    target_row_id   INTEGER NOT NULL,
    source_system   TEXT    NOT NULL,
    transformation  TEXT    NOT NULL,
    engine          TEXT,
    timestamp       TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_lineage_target ON data_lineage(target_table, target_row_id);

-- =============================================================================
-- XXV. CORPORATE ACTIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS corporate_actions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER NOT NULL REFERENCES stocks(id),
    action_type     TEXT    NOT NULL CHECK(action_type IN ('SPLIT','BONUS','RIGHTS','DIVIDEND','MERGER','DEMERGER','SYMBOL_CHANGE')),
    ex_date         TEXT    NOT NULL,
    ratio_old       REAL,
    ratio_new       REAL,
    amount          REAL,
    applied         INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ca_stock ON corporate_actions(stock_id, ex_date DESC);

-- =============================================================================
-- XXVI. DATA SOURCE HEALTH
-- =============================================================================
CREATE TABLE IF NOT EXISTS data_source_health (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT    NOT NULL UNIQUE,
    status          TEXT    NOT NULL DEFAULT 'HEALTHY' CHECK(status IN ('HEALTHY','WARNING','CRITICAL')),
    last_update     TEXT,
    expected_update TEXT,
    failure_count   INTEGER DEFAULT 0,
    recovery_status TEXT    DEFAULT 'N/A'
);

-- =============================================================================
-- XXVII. DATA ANOMALIES
-- =============================================================================
CREATE TABLE IF NOT EXISTS data_anomalies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id        INTEGER REFERENCES stocks(id),
    anomaly_type    TEXT    NOT NULL CHECK(anomaly_type IN ('PRICE_GAP','VOLUME_SPIKE','MARKET_CAP_CHANGE','SECTOR_CHANGE','PROMOTER_CHANGE')),
    description     TEXT    NOT NULL,
    detected_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    resolved        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_anomalies_date ON data_anomalies(detected_at DESC);

-- =============================================================================
-- XXVIII. SYSTEM METRICS
-- =============================================================================
CREATE TABLE IF NOT EXISTS system_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name     TEXT    NOT NULL,
    metric_value    REAL    NOT NULL,
    tags            TEXT,
    timestamp       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- =============================================================================
-- XXIX. TELEMETRY LOGS
-- =============================================================================
CREATE TABLE IF NOT EXISTS telemetry_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action_name     TEXT    NOT NULL,
    result          TEXT    NOT NULL,
    duration_ms     REAL    NOT NULL,
    status          TEXT    NOT NULL CHECK(status IN ('SUCCESS','FAILURE','WARNING')),
    timestamp       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- =============================================================================
-- XXX. SYSTEM ERRORS
-- =============================================================================
CREATE TABLE IF NOT EXISTS system_errors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name    TEXT    NOT NULL,
    severity        TEXT    NOT NULL CHECK(severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    error_message   TEXT    NOT NULL,
    recovery_status TEXT    DEFAULT 'PENDING',
    timestamp       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- =============================================================================
-- XXXI. STRATEGY REGISTRY
-- =============================================================================
CREATE TABLE IF NOT EXISTS strategy_registry (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    version         TEXT    NOT NULL,
    parameters      TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT','TESTING','APPROVED','REJECTED','ARCHIVED')),
    created_date    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- =============================================================================
-- XXXII. RESEARCH RUNS
-- =============================================================================
CREATE TABLE IF NOT EXISTS research_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id     INTEGER REFERENCES strategy_registry(id),
    run_date        TEXT    NOT NULL DEFAULT (datetime('now')),
    parameters      TEXT    NOT NULL,
    notes           TEXT
);

-- =============================================================================
-- XXXIII. BACKTEST RESULTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS backtest_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER REFERENCES research_runs(id),
    cagr            REAL,
    xirr            REAL,
    sharpe          REAL,
    sortino         REAL,
    max_drawdown    REAL,
    win_rate        REAL,
    profit_factor   REAL,
    expectancy      REAL,
    total_trades    INTEGER
);

-- =============================================================================
-- XXXIV. WALKFORWARD RESULTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS walkforward_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER REFERENCES research_runs(id),
    period_start    TEXT,
    period_end      TEXT,
    train_sharpe    REAL,
    test_sharpe     REAL,
    sharpe_decay    REAL,
    stability_score REAL
);

-- =============================================================================
-- XXXV. MONTE CARLO RESULTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS monte_carlo_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER REFERENCES research_runs(id),
    simulations     INTEGER DEFAULT 10000,
    prob_loss       REAL,
    prob_ruin       REAL,
    expected_dd     REAL,
    cagr_5th        REAL,
    cagr_95th       REAL
);

-- =============================================================================
-- XXXVI. FACTOR ANALYSIS RESULTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS factor_analysis_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER REFERENCES research_runs(id),
    factor_name     TEXT,
    importance      REAL
);
