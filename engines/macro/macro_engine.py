"""
HFOS v5.0 — Macro Engine
Scores macroeconomic conditions affecting Indian equity markets.
RBI rates, inflation, USD/INR, FII flows, GDP growth.
"""
import logging
from typing import Optional
from database.db_manager import execute_one

logger = logging.getLogger(__name__)


class MacroEngine:
    """
    Macro Score: 0-100 (higher = more favorable macro environment)
    Components:
      Interest Rates   (25%): RBI repo rate direction
      Inflation        (20%): CPI vs target
      Currency         (20%): INR strength vs USD
      FII Flows        (20%): Net FII buying/selling
      GDP/PMI          (15%): Growth indicators
    """

    # RBI target CPI band: 2-6%, ideal ~4%
    CPI_TARGET    = 4.0
    CPI_UPPER     = 6.0
    REPO_IDEAL    = 5.5    # Rate cut cycle positive
    INR_DANGER    = 87.0   # INR/USD above this = concern

    def score(self, macro_data: Optional[dict] = None) -> float:
        """
        Args:
            macro_data: dict with keys: repo_rate, cpi, inr_usd,
                        fii_net_cr (7-day), gdp_growth_pct
        Returns: float 0-100
        """
        try:
            data = macro_data or self._fetch_macro_snapshot()
            components = {
                "rates":    self._rate_score(data),
                "inflation":self._inflation_score(data),
                "currency": self._currency_score(data),
                "fii":      self._fii_score(data),
                "growth":   self._growth_score(data),
            }
            weights = {
                "rates": 0.25, "inflation": 0.20, "currency": 0.20,
                "fii": 0.20, "growth": 0.15,
            }
            composite = sum(components[k] * weights[k] for k in components)
            result = round(max(0.0, min(100.0, composite)), 2)
            logger.debug(f"MacroScore={result:.1f} components={components}")
            return result
        except Exception as e:
            logger.error(f"MacroEngine error: {e}")
            return 50.0

    # -------------------------------------------------------------------------
    def _rate_score(self, d: dict) -> float:
        repo = d.get("repo_rate", 6.5)
        if repo <= 5.0:   return 85.0   # Accommodative — very bullish
        if repo <= 5.5:   return 75.0
        if repo <= 6.0:   return 65.0
        if repo <= 6.5:   return 55.0   # Neutral
        if repo <= 7.0:   return 40.0   # Tightening
        return 25.0                      # Very tight

    def _inflation_score(self, d: dict) -> float:
        cpi = d.get("cpi", 4.5)
        if cpi <= self.CPI_TARGET:      return 80.0  # Below target = dovish
        if cpi <= 5.0:                  return 65.0
        if cpi <= self.CPI_UPPER:       return 50.0  # Within band
        if cpi <= 7.0:                  return 30.0  # Above band
        return 10.0                                   # Runaway inflation

    def _currency_score(self, d: dict) -> float:
        inr = d.get("inr_usd", 83.5)
        if inr < 80.0:   return 85.0   # Strong INR — FII positive
        if inr < 82.0:   return 72.0
        if inr < 84.0:   return 60.0   # Normal range
        if inr < 86.0:   return 45.0   # Weak INR
        if inr < self.INR_DANGER: return 30.0
        return 15.0                    # Crisis territory

    def _fii_score(self, d: dict) -> float:
        fii_net = d.get("fii_net_cr", 0.0)  # Rs Cr, positive = buying
        if fii_net > 5000:   return 90.0
        if fii_net > 2000:   return 75.0
        if fii_net > 0:      return 60.0
        if fii_net > -2000:  return 45.0
        if fii_net > -5000:  return 30.0
        return 15.0

    def _growth_score(self, d: dict) -> float:
        gdp = d.get("gdp_growth_pct", 6.5)
        pmi = d.get("pmi_manufacturing", 54.0)

        score = 0.0
        if gdp >= 7.5:   score += 50.0
        elif gdp >= 6.5: score += 40.0
        elif gdp >= 5.5: score += 28.0
        elif gdp >= 4.0: score += 15.0
        else:            score += 5.0

        if pmi and pmi >= 55:    score += 50.0
        elif pmi and pmi >= 52:  score += 35.0
        elif pmi and pmi >= 50:  score += 20.0
        else:                    score += 5.0

        return min(100.0, score)

    def _fetch_macro_snapshot(self) -> dict:
        """Pull latest FII data from DB; use configured defaults for other indicators."""
        snapshot = {
            "repo_rate":          6.5,
            "cpi":                4.8,
            "inr_usd":            83.5,
            "fii_net_cr":         0.0,
            "gdp_growth_pct":     6.8,
            "pmi_manufacturing":  54.0,
        }
        try:
            row = execute_one(
                """SELECT fii_net_cr FROM fii_dii_activity
                   ORDER BY activity_date DESC LIMIT 1"""
            )
            if row:
                snapshot["fii_net_cr"] = row["fii_net_cr"] or 0.0
        except Exception as e:
            logger.debug(f"Macro DB fetch failed: {e}")
        return snapshot
