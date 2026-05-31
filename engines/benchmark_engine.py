"""HFOS v5.0 — Benchmark Engine (Real Implementation)

Computes actual alpha, beta, tracking error vs benchmark price series.
No randomized values.
"""
import numpy as np
from typing import Optional


class BenchmarkEngine:
    """Computes strategy performance vs benchmark using actual returns."""

    def run(self, portfolio_prices: list, benchmark_prices: list) -> dict:
        """
        Args:
            portfolio_prices: Strategy daily price series.
            benchmark_prices: Benchmark (e.g. Nifty 50) daily price series.
        Returns:
            dict with alpha, beta, info_ratio, tracking_error, correlation.
        """
        if len(portfolio_prices) < 2 or len(benchmark_prices) < 2:
            raise ValueError("BenchmarkEngine requires at least 2 price points in each series.")

        p = np.array(portfolio_prices, dtype=float)
        b = np.array(benchmark_prices, dtype=float)

        # Align lengths
        min_len = min(len(p), len(b))
        p = p[:min_len]
        b = b[:min_len]

        p_ret = np.diff(p) / p[:-1]
        b_ret = np.diff(b) / b[:-1]

        # Beta via linear regression
        cov_matrix = np.cov(p_ret, b_ret)
        beta = float(cov_matrix[0, 1] / cov_matrix[1, 1]) if cov_matrix[1, 1] != 0 else 1.0

        # Alpha (Jensen's alpha annualized)
        risk_free_daily = 0.065 / 252
        alpha_daily = (p_ret.mean() - risk_free_daily) - beta * (b_ret.mean() - risk_free_daily)
        alpha_annual = alpha_daily * 252 * 100  # in %

        # Tracking error (annualized std of excess returns)
        active_returns = p_ret - b_ret
        tracking_error = float(active_returns.std() * np.sqrt(252) * 100)  # %

        # Information ratio
        info_ratio = float(active_returns.mean() / active_returns.std() * np.sqrt(252)) \
            if active_returns.std() > 0 else 0.0

        # Correlation
        correlation = float(np.corrcoef(p_ret, b_ret)[0, 1])

        return {
            "alpha_annual_pct": round(alpha_annual, 4),
            "beta":             round(beta, 4),
            "tracking_error":   round(tracking_error, 4),
            "information_ratio": round(info_ratio, 4),
            "correlation":      round(correlation, 4),
            "n_periods":        min_len - 1,
        }

    def compare(self, strategy_cagr: float, strategy_vol: float) -> list:
        """Legacy interface for UI display — compares known CAGR vs fixed benchmarks."""
        nifty_cagr    = 12.5
        nifty500_cagr = 14.0
        return [
            {
                "benchmark": "Nifty 50",
                "alpha": round(strategy_cagr - nifty_cagr, 2),
                "strategy_vol": strategy_vol,
            },
            {
                "benchmark": "Nifty 500",
                "alpha": round(strategy_cagr - nifty500_cagr, 2),
                "strategy_vol": strategy_vol,
            },
        ]
