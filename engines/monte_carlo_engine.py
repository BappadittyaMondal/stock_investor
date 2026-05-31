"""HFOS v5.0 — Monte Carlo Engine (Real Implementation)

Runs N simulations by resampling actual historical returns (bootstrap).
No fake random uniform calls. Output is statistically derived from real data.
"""
import numpy as np
from typing import Optional


class MonteCarloEngine:
    """Bootstrap Monte Carlo simulation on historical return distribution."""

    def run(self, prices: list, simulations: int = 5000, horizon_days: int = 252) -> dict:
        """
        Args:
            prices: Historical daily price series.
            simulations: Number of Monte Carlo paths.
            horizon_days: Forecast horizon in trading days (default 1 year).
        Returns:
            dict with probability of loss, probability of ruin, CAGR percentiles.
        """
        if len(prices) < 30:
            raise ValueError("MonteCarloEngine requires at least 30 price points.")

        arr = np.array(prices, dtype=float)
        daily_returns = np.diff(arr) / arr[:-1]

        # Bootstrap: resample with replacement from historical return distribution
        rng = np.random.default_rng(seed=42)  # deterministic seed for reproducibility
        sampled = rng.choice(daily_returns, size=(simulations, horizon_days), replace=True)
        paths = np.cumprod(1 + sampled, axis=1)

        final_values = paths[:, -1]  # terminal portfolio multiplier

        # Statistics
        prob_loss = float(np.mean(final_values < 1.0))
        prob_ruin = float(np.mean(final_values < 0.5))  # >50% loss = ruin

        # CAGR from terminal value
        cagr_vals = (final_values ** (252.0 / horizon_days) - 1.0) * 100

        # Max drawdowns across paths
        peaks = np.maximum.accumulate(paths, axis=1)
        drawdowns = (paths - peaks) / peaks
        expected_dd = float(np.mean(drawdowns.min(axis=1))) * 100

        return {
            "simulations":    simulations,
            "horizon_days":   horizon_days,
            "prob_loss":      round(prob_loss, 4),
            "prob_ruin":      round(prob_ruin, 4),
            "expected_dd":    round(expected_dd, 2),       # %
            "cagr_5th":       round(float(np.percentile(cagr_vals, 5)), 2),
            "cagr_50th":      round(float(np.percentile(cagr_vals, 50)), 2),
            "cagr_95th":      round(float(np.percentile(cagr_vals, 95)), 2),
            "seed":           42,  # reproducibility
        }
