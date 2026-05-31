"""
HFOS v5.0 — Risk Engine
Scores 0-100 where HIGHER = MORE risky (inverted in AlphaEngine).
"""
import logging
from typing import Optional
import numpy as np
import pandas as pd

from database.db_manager import execute_one

logger = logging.getLogger(__name__)


class RiskEngine:
    """
    Risk Score: 0-100 (higher = more risky)
    AlphaEngine uses (100 - risk_score).
    Components:
      ASM/GSM Flags   (25%): Hard penalty
      Pledge          (20%): Promoter pledge %
      Debt            (15%): Debt/Equity ratio
      Auditor Flags   (15%): Qualified opinion, going concern
      Governance      (10%): Related party, litigation
      Price Volatility(10%): Historical beta/SD
      Liquidity        (5%): Market cap + avg daily volume
    """

    def score(self, stock_data: dict, ohlcv_df: Optional[pd.DataFrame] = None) -> float:
        """
        Args:
            stock_data: dict with stock + fundamental fields
            ohlcv_df: optional OHLCV for volatility calculation
        Returns: float 0-100 (higher = riskier)
        """
        try:
            components = {
                "regulatory":  self._regulatory_score(stock_data),
                "pledge":      self._pledge_score(stock_data),
                "debt":        self._debt_score(stock_data),
                "auditor":     self._auditor_score(stock_data),
                "governance":  self._governance_score(stock_data),
                "volatility":  self._volatility_score(ohlcv_df),
                "liquidity":   self._liquidity_score(stock_data),
            }
            weights = {
                "regulatory": 0.25, "pledge": 0.20, "debt": 0.15,
                "auditor": 0.15, "governance": 0.10, "volatility": 0.10,
                "liquidity": 0.05,
            }
            composite = sum(components[k] * weights[k] for k in components)
            result = round(max(0.0, min(100.0, composite)), 2)
            logger.debug(f"RiskScore={result:.1f} components={components}")
            return result
        except Exception as e:
            logger.error(f"RiskEngine error: {e}")
            return 50.0

    def score_from_db(self, stock_id: int, ohlcv_df: Optional[pd.DataFrame] = None) -> float:
        stock = execute_one("SELECT * FROM stocks WHERE id=?", (stock_id,))
        fund  = execute_one(
            "SELECT * FROM fundamentals WHERE stock_id=? ORDER BY report_date DESC LIMIT 1",
            (stock_id,)
        )
        if not stock:
            return 50.0
        merged = dict(stock)
        if fund:
            merged.update(dict(fund))
        return self.score(merged, ohlcv_df)

    # -------------------------------------------------------------------------
    def _regulatory_score(self, d: dict) -> float:
        """ASM/GSM flags are disqualifying — max risk."""
        score = 0.0
        if d.get("asm_flag"):  score += 60.0
        if d.get("gsm_flag"):  score += 80.0
        return min(100.0, score)

    def _pledge_score(self, d: dict) -> float:
        pledge = d.get("pledged_pct", 0.0) or d.get("pledge_pct", 0.0) or 0.0
        if pledge >= 80:  return 100.0
        if pledge >= 60:  return 80.0
        if pledge >= 40:  return 60.0
        if pledge >= 20:  return 35.0
        if pledge >= 10:  return 15.0
        return 5.0

    def _debt_score(self, d: dict) -> float:
        de = d.get("debt_equity")
        if de is None:   return 40.0  # unknown = moderate risk
        if de >= 5.0:    return 100.0
        if de >= 3.0:    return 80.0
        if de >= 2.0:    return 60.0
        if de >= 1.0:    return 40.0
        if de >= 0.5:    return 20.0
        return 5.0

    def _auditor_score(self, d: dict) -> float:
        """Check auditor qualification flags."""
        score = 0.0
        if d.get("auditor_qualified"):      score += 60.0
        if d.get("going_concern"):          score += 80.0
        if d.get("auditor_changed"):        score += 20.0
        if d.get("fraudulent_reporting"):   score += 100.0
        return min(100.0, score)

    def _governance_score(self, d: dict) -> float:
        score = 0.0
        if d.get("related_party_high"):     score += 40.0
        if d.get("litigation_pending"):     score += 25.0
        if d.get("sebi_action"):            score += 50.0
        if d.get("promoter_selling"):       score += 20.0
        # Low promoter holding = governance concern
        prom = d.get("promoter_holding")
        if prom is not None and prom < 25:  score += 20.0
        return min(100.0, score)

    def _volatility_score(self, df: Optional[pd.DataFrame]) -> float:
        """Historical annualised volatility → risk score."""
        if df is None or len(df) < 30:
            return 40.0  # unknown = moderate
        try:
            returns = df["close"].pct_change().dropna()
            ann_vol = returns.std() * np.sqrt(252) * 100  # in %
            if ann_vol >= 80:
                return 100.0
            if ann_vol >= 60:
                return 80.0
            if ann_vol >= 40:
                return 60.0
            if ann_vol >= 25:
                return 40.0
            if ann_vol >= 15:
                return 20.0
            return 10.0
        except Exception:
            return 40.0

    def _liquidity_score(self, d: dict) -> float:
        """Market cap and average daily volume liquidity risk.
        Small-cap (<500cr) and illiquid stocks carry higher institutional risk.
        """
        score = 0.0
        mcap = d.get("market_cap_cr")
        if mcap is not None:
            if mcap < 100:
                score += 80.0
            elif mcap < 500:
                score += 60.0
            elif mcap < 1000:
                score += 40.0
            elif mcap < 5000:
                score += 20.0
            else:
                score += 5.0
        else:
            score += 40.0  # unknown
        vol = d.get("avg_daily_vol")
        if vol is not None:
            if vol < 50_000:
                score += 20.0
            elif vol < 200_000:
                score += 10.0
            else:
                score += 0.0
        return min(100.0, score)
