"""
HFOS v5.0 — Policy Engine
Scores policy tailwinds from PIB/RBI/SEBI news and pre-configured themes.
"""
import logging
from datetime import datetime, timedelta
from database.db_manager import execute_query

logger = logging.getLogger(__name__)

# Policy theme → affected sectors
POLICY_THEMES: dict[str, dict] = {
    "PLI_SCHEME": {
        "sectors": ["Auto", "Pharma", "Chemicals", "Capital Goods", "Textile"],
        "score_boost": 20.0,
        "active": True,
    },
    "ATMANIRBHAR_DEFENCE": {
        "sectors": ["Defence"],
        "score_boost": 25.0,
        "active": True,
    },
    "NATIONAL_INFRASTRUCTURE_PIPELINE": {
        "sectors": ["Infrastructure", "Capital Goods", "Cement", "Steel"],
        "score_boost": 22.0,
        "active": True,
    },
    "GREEN_HYDROGEN_MISSION": {
        "sectors": ["Renewable Energy", "Chemicals"],
        "score_boost": 18.0,
        "active": True,
    },
    "DIGITAL_INDIA": {
        "sectors": ["IT", "Telecom"],
        "score_boost": 12.0,
        "active": True,
    },
    "STARTUP_INDIA": {
        "sectors": ["IT", "Fintech"],
        "score_boost": 8.0,
        "active": True,
    },
    "HOUSING_FOR_ALL": {
        "sectors": ["Real Estate", "Cement", "Steel"],
        "score_boost": 15.0,
        "active": True,
    },
    "PM_KISAN_AGRICULTURE": {
        "sectors": ["Agrochemicals", "FMCG", "Rural"],
        "score_boost": 10.0,
        "active": True,
    },
}

POLICY_NEGATIVE_KEYWORDS = {
    "tax hike", "duty increase", "ban", "restriction", "penalty",
    "windfall tax", "price control", "nationalization",
}
POLICY_POSITIVE_KEYWORDS = {
    "incentive", "subsidy", "pli", "scheme", "approval", "boost",
    "allocation", "fund", "capex", "reform", "ease",
}


class PolicyEngine:
    """
    Policy Score: 0-100
    Components:
      Sector-Theme Match  (50%): Active policy themes affecting this sector
      Recent Policy News  (30%): PIB/RBI/SEBI sentiment last 30 days
      Regulatory Environment (20%): SEBI regulations, FDI rules
    """

    def score(self, sector: str, symbol: str = "") -> float:
        try:
            theme_score   = self._theme_score(sector)
            news_score    = self._policy_news_score(sector, symbol)
            reg_score     = self._regulatory_score()

            composite = (
                theme_score * 0.50
                + news_score * 0.30
                + reg_score  * 0.20
            )
            result = round(max(0.0, min(100.0, composite)), 2)
            logger.debug(f"PolicyScore[{sector}]={result:.1f}")
            return result
        except Exception as e:
            logger.error(f"PolicyEngine error: {e}")
            return 50.0

    # -------------------------------------------------------------------------
    def _theme_score(self, sector: str) -> float:
        base = 50.0
        for theme_name, theme in POLICY_THEMES.items():
            if theme["active"] and sector in theme["sectors"]:
                base += theme["score_boost"]
        return min(100.0, base)

    def _policy_news_score(self, sector: str, symbol: str) -> float:
        """Score from DB-stored news tagged to government/regulator sources."""
        try:
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            rows = execute_query(
                """SELECT sentiment_score FROM news_items
                   WHERE source IN ('PIB','RBI','SEBI')
                   AND published_at > ?
                   AND sentiment_score IS NOT NULL""",
                (cutoff,)
            )
            if not rows:
                return 50.0
            avg = sum(r["sentiment_score"] for r in rows) / len(rows)
            return (avg + 1.0) * 50.0
        except Exception:
            return 50.0

    def _regulatory_score(self) -> float:
        """Base regulatory environment score for Indian equity markets."""
        # SEBI has been improving disclosure/governance — baseline positive
        return 65.0
