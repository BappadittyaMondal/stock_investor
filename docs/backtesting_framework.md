# HFOS v5.0 — Backtesting Framework

## Overview
The Backtesting Framework is responsible for recreating historical trade ledgers using historical OHLCV and fundamental records. 

## Engine Execution
Located in `engines/backtest_engine.py`, the engine calculates:
- **CAGR & XIRR**: To measure annualized capital growth.
- **Sharpe & Sortino**: To measure risk-adjusted return and downside volatility.
- **Max Drawdown**: To measure the worst-case historical scenario.
- **Expectancy**: Average PnL per trade multiplied by win rate.

## Regime Analysis
Strategies are implicitly tested across market regimes (e.g. COVID crash, 2021 bull run, 2022 sideways market). The benchmark engine (`benchmark_engine.py`) explicitly tracks the strategy's Alpha generation against the Nifty 50 and Nifty 500 during these periods to ensure true edge, not just beta riding.
