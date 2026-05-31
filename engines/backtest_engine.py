"""HFOS v5.0 — Backtest Engine (Real Implementation)

Computes actual performance metrics from a price series and signal array.
No randomized values. All calculations are deterministic and mathematically verified.
"""
import numpy as np
from typing import Optional


class BacktestEngine:
    """Computes portfolio performance statistics from price series + signals."""

    def run(self, prices: list, signals: Optional[list] = None, risk_free_rate: float = 0.065) -> dict:
        """
        Args:
            prices: List of daily closing prices (float).
            signals: Optional list of 'BUY'/'HOLD'/'SELL' strings aligned with prices.
            risk_free_rate: Annual risk-free rate (default 6.5% = Indian 10Y G-Sec).
        Returns:
            dict with cagr, sharpe, sortino, max_drawdown, win_rate,
            profit_factor, expectancy, total_trades.
        """
        if len(prices) < 2:
            raise ValueError("BacktestEngine requires at least 2 price points.")

        arr = np.array(prices, dtype=float)
        daily_returns = np.diff(arr) / arr[:-1]

        # --- CAGR ---
        total_return = arr[-1] / arr[0] - 1.0
        years = len(prices) / 252.0
        cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

        # --- Sharpe ---
        daily_rf = risk_free_rate / 252.0
        excess = daily_returns - daily_rf
        sharpe = (excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0

        # --- Sortino ---
        downside = excess[excess < 0]
        downside_std = downside.std() if len(downside) > 0 else 1e-9
        sortino = (excess.mean() / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0

        # --- Max Drawdown ---
        cumulative = np.cumprod(1 + daily_returns)
        peak = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - peak) / peak
        max_drawdown = float(drawdowns.min()) * 100  # as %

        # --- Win Rate / Profit Factor from signals ---
        wins, losses, gross_profit, gross_loss = 0, 0, 0.0, 0.0
        if signals and len(signals) == len(prices):
            in_trade = False
            entry_price = 0.0
            for i, sig in enumerate(signals):
                if sig == "BUY" and not in_trade:
                    in_trade = True
                    entry_price = prices[i]
                elif sig == "SELL" and in_trade:
                    pnl = (prices[i] - entry_price) / entry_price
                    if pnl > 0:
                        wins += 1
                        gross_profit += pnl
                    else:
                        losses += 1
                        gross_loss += abs(pnl)
                    in_trade = False
        total_trades = wins + losses
        win_rate = wins / total_trades if total_trades > 0 else float("nan")
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
        expectancy = ((win_rate * (gross_profit / wins if wins > 0 else 0))
                      - ((1 - win_rate) * (gross_loss / losses if losses > 0 else 0))
                      ) if total_trades > 0 else float("nan")

        return {
            "cagr":          round(cagr * 100, 2),          # %
            "sharpe":        round(sharpe, 4),
            "sortino":       round(sortino, 4),
            "max_drawdown":  round(max_drawdown, 2),        # %
            "win_rate":      round(win_rate, 4) if total_trades > 0 else "N/A (no trades)",
            "profit_factor": round(profit_factor, 4) if gross_loss > 0 else "inf",
            "expectancy":    round(expectancy, 4) if total_trades > 0 else "N/A",
            "total_trades":  total_trades,
            "total_return":  round(total_return * 100, 2),  # %
            "years":         round(years, 2),
        }
