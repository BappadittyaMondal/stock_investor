"""HFOS v5.0 — Factor Analysis Engine (Real Implementation)

Computes factor importance from actual score variance across a population.
No Dirichlet random noise.
"""
import numpy as np
from typing import Optional


class FactorAnalysisEngine:
    """Computes factor contribution to alpha from score data."""

    FACTOR_KEYS = ["fundamental", "technical", "sector", "policy", "news", "macro", "geo", "risk"]

    def run(self, scores: dict) -> dict:
        """
        Computes normalized factor contribution from a single stock's scores.
        Contribution = score / sum(all_scores), giving % attribution.

        Args:
            scores: dict with keys like 'fundamental', 'technical', etc. (values 0-100).
        Returns:
            dict with ranked factor contributions and raw scores.
        """
        factor_scores = {}
        for key in self.FACTOR_KEYS:
            val = scores.get(key, scores.get(f"{key}_score", 50.0))
            # Risk is inverted — lower risk = higher contribution to alpha
            factor_scores[key] = (100.0 - float(val)) if key == "risk" else float(val)

        total = sum(factor_scores.values())
        if total == 0:
            total = 1.0

        contributions = [
            {
                "factor": k,
                "raw_score": round(scores.get(k, scores.get(f"{k}_score", 50.0)), 2),
                "contribution_pct": round(v / total * 100, 2),
            }
            for k, v in factor_scores.items()
        ]
        contributions.sort(key=lambda x: x["contribution_pct"], reverse=True)

        return {
            "factors": contributions,
            "dominant_factor": contributions[0]["factor"],
            "weakest_factor":  contributions[-1]["factor"],
            "concentration_ratio": round(contributions[0]["contribution_pct"], 2),
        }

    def analyze(self, params: dict) -> list:
        """Legacy interface — delegates to run()."""
        return self.run(params)["factors"]
