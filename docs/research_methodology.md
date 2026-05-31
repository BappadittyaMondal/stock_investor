# HFOS v5.0 — Research Methodology

## Core Philosophy
No strategy may reach production without passing Walk-Forward validation. Static backtests are prone to overfitting.

## Validation Steps
1. **Backtest**: Standard historical pass. If Sharpe < 1.0, reject.
2. **Walk-Forward Validation (`walkforward_engine.py`)**: The model is trained on an expanding window (e.g., 2015-2019) and tested on the out-of-sample following year (2020). 
   - We calculate **Sharpe Decay**. If the out-of-sample Sharpe drops significantly (> 50% decay) from the in-sample Sharpe, the model is curve-fitted and rejected.
3. **Monte Carlo Simulation (`monte_carlo_engine.py`)**: The historical trade sequence is resampled 10,000 times to calculate the "Probability of Ruin" and the 5th percentile worst-case CAGR.
4. **Factor Attribution (`factor_analysis_engine.py`)**: Determines *why* the strategy makes money. (e.g., 60% Technical Momentum, 40% Fundamental Value).

## Strategy Registry
Strategies that pass are inserted into the `strategy_registry` table as `APPROVED`, meaning they can be selected by the core `AlphaEngine` for live scoring.
