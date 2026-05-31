"""
HFOS v5.0 — Fundamental Engine
Scores 0-100 from screener.in data + cached fundamentals.
"""
import logging
from typing import Optional
from database.db_manager import execute_one

logger = logging.getLogger(__name__)


class FundamentalEngine:
    """
    Fundamental Score: 0-100
    Components:
      Profitability  (25%): ROE, ROCE, PAT margin
      Growth         (25%): Revenue growth, PAT growth YoY
      Valuation      (20%): PE, PB vs sector median
      Quality        (15%): Debt/Equity, Current ratio, Promoter holding
      Capital Alloc  (15%): FCF, Dividend yield, Operating CF
    """

    SECTOR_PE_MEDIANS: dict[str, float] = {
        "IT":            25.0,
        "Banking":       15.0,
        "FMCG":          50.0,
        "Auto":          20.0,
        "Pharma":        30.0,
        "Metals":        10.0,
        "Energy":        12.0,
        "Infrastructure": 18.0,
        "Chemicals":     28.0,
        "Realty":        20.0,
        "Default":       22.0,
    }

    def score(self, fund: dict, sector: Optional[str] = None) -> float:
        """
        Args:
            fund: dict matching fundamentals table columns
            sector: optional sector for PE comparison
        Returns: float 0-100
        """
        if not fund:
            return 50.0
        try:
            scores = {
                "profitability": self._profitability(fund),
                "growth":        self._growth(fund),
                "valuation":     self._valuation(fund, sector),
                "quality":       self._quality(fund),
                "capital_alloc": self._capital_alloc(fund),
            }
            weights = {
                "profitability": 0.25, "growth": 0.25, "valuation": 0.20,
                "quality": 0.15, "capital_alloc": 0.15,
            }
            composite = sum(scores[k] * weights[k] for k in scores)
            result = round(max(0.0, min(100.0, composite)), 2)
            logger.debug(f"FundScore={result:.1f} components={scores}")
            return result
        except Exception as e:
            logger.error(f"FundamentalEngine error: {e}")
            return 50.0

    def score_from_db(self, stock_id: int) -> float:
        """Load latest fundamentals from DB and score."""
        row = execute_one(
            """SELECT * FROM fundamentals
               WHERE stock_id=? ORDER BY report_date DESC LIMIT 1""",
            (stock_id,)
        )
        if not row:
            return 50.0
        return self.score(dict(row))

    # -------------------------------------------------------------------------
    def _profitability(self, f: dict) -> float:
        score = 0.0
        roe   = f.get("roe_pct")
        roce  = f.get("roce_pct")
        rev   = f.get("revenue_cr") or 0
        pat   = f.get("pat_cr")

        if roe is not None:
            if roe > 25: score += 35.0
            elif roe > 15: score += 25.0
            elif roe > 10: score += 15.0
            elif roe > 5:  score += 8.0

        if roce is not None:
            if roce > 25: score += 35.0
            elif roce > 18: score += 25.0
            elif roce > 12: score += 15.0
            elif roce > 8:  score += 8.0

        if rev > 0 and pat is not None:
            margin = (pat / rev) * 100
            if margin > 20: score += 30.0
            elif margin > 12: score += 20.0
            elif margin > 6:  score += 10.0
            elif margin > 0:  score += 5.0

        return min(100.0, score)

    def _growth(self, f: dict) -> float:
        score = 0.0
        rev_g = f.get("revenue_growth_yoy")
        pat_g = f.get("pat_growth_yoy")

        if rev_g is not None:
            if rev_g > 25: score += 45.0
            elif rev_g > 15: score += 35.0
            elif rev_g > 8:  score += 20.0
            elif rev_g > 0:  score += 10.0

        if pat_g is not None:
            if pat_g > 30: score += 55.0
            elif pat_g > 20: score += 40.0
            elif pat_g > 10: score += 25.0
            elif pat_g > 0:  score += 10.0

        return min(100.0, score)

    def _valuation(self, f: dict, sector: Optional[str]) -> float:
        score = 50.0  # neutral default
        pe  = f.get("pe_ratio")
        pb  = f.get("pb_ratio")
        median_pe = self.SECTOR_PE_MEDIANS.get(sector or "Default",
                     self.SECTOR_PE_MEDIANS["Default"])

        if pe is not None and pe > 0:
            ratio = pe / median_pe
            if ratio < 0.7:   score = min(100.0, score + 30.0)  # cheap
            elif ratio < 0.9: score = min(100.0, score + 15.0)
            elif ratio < 1.1: pass                               # fair
            elif ratio < 1.5: score = max(0.0, score - 15.0)
            else:             score = max(0.0, score - 30.0)     # expensive

        if pb is not None and pb > 0:
            if pb < 1.5:    score = min(100.0, score + 20.0)
            elif pb < 3.0:  score = min(100.0, score + 10.0)
            elif pb > 10.0: score = max(0.0, score - 20.0)

        return score

    def _quality(self, f: dict) -> float:
        score = 0.0
        de   = f.get("debt_equity")
        cr   = f.get("current_ratio")
        prom = f.get("promoter_holding")
        pledge = f.get("pledged_pct", 0.0) or 0.0

        if de is not None:
            if de < 0.3:  score += 35.0
            elif de < 0.7: score += 25.0
            elif de < 1.0: score += 15.0
            elif de < 2.0: score += 5.0

        if cr is not None:
            if cr > 2.0:  score += 30.0
            elif cr > 1.5: score += 20.0
            elif cr > 1.0: score += 10.0

        if prom is not None:
            if prom > 60: score += 25.0
            elif prom > 50: score += 18.0
            elif prom > 35: score += 10.0

        # Pledge penalty
        if pledge > 50:  score -= 20.0
        elif pledge > 30: score -= 10.0
        elif pledge > 15: score -= 5.0

        return max(0.0, min(100.0, score))

    def _capital_alloc(self, f: dict) -> float:
        score = 50.0
        fcf  = f.get("fcf_cr")
        ocf  = f.get("operating_cf")
        div  = f.get("dividend_yield", 0.0) or 0.0

        if fcf is not None:
            if fcf > 0:   score = min(100.0, score + 30.0)
            else:         score = max(0.0, score - 20.0)

        if ocf is not None:
            if ocf > 0:   score = min(100.0, score + 15.0)
            else:         score = max(0.0, score - 10.0)

        if div > 3.0:   score = min(100.0, score + 10.0)
        elif div > 1.0: score = min(100.0, score + 5.0)

        return score
