# HFOS v5.0 — Strategy Validation Report

## Validation Output Example
When a Portfolio Manager executes a run in the **Research Lab**, the AI Copilot interprets the multidimensional outputs of the Backtest, Walk-Forward, Monte Carlo, and Factor Analysis engines.

### 1. Robustness
A strategy is deemed robust if it passes the Walk-Forward test with a `Stability Score > 50`. This implies the model's Sharpe Ratio does not degrade significantly when applied to unseen, out-of-sample market conditions.

### 2. Risk Management (Monte Carlo)
The Monte Carlo simulation exposes tail risks. A strategy with a strong CAGR but a `Probability of Ruin > 2%` is automatically flagged as excessively risky, requiring tighter Stop Loss constraints.

### 3. Factor Dependence
By breaking down the returns, the `FactorAnalysisEngine` ensures the strategy aligns with the intended thesis. If a "Value Strategy" derives 70% of its returns from the `Technical` factor rather than the `Fundamental` factor, the validation report flags a misalignment in the weighting logic.

Only strategies possessing a pristine validation report may be promoted to `APPROVED` status in the `strategy_registry`.
