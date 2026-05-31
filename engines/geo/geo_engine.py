"""
HFOS v5.0 — Geo-Political Engine
Scores geopolitical risk impact on Indian equity markets.
"""
import logging
from datetime import datetime, timedelta
from database.db_manager import execute_query

logger = logging.getLogger(__name__)

SEVERITY_SCORES = {
    "CRITICAL": 90,
    "HIGH":     65,
    "MEDIUM":   40,
    "LOW":      15,
}

EVENT_TYPE_SECTOR_MAP = {
    "BORDER_TENSION":   ["Defence", "Infrastructure"],
    "TRADE_WAR":        ["IT", "Auto", "Metals", "Chemicals"],
    "SANCTIONS":        ["Energy", "Metals"],
    "OIL_SHOCK":        ["Energy", "Auto", "FMCG", "Airlines"],
    "CURRENCY_CRISIS":  ["IT", "Pharma"],   # INR depreciation beneficiaries
    "ELECTION":         ["Infrastructure", "FMCG", "Rural"],
    "RBI_POLICY":       ["Banking", "Real Estate", "Auto"],
    "SEBI_REGULATION":  ["Capital Markets"],
}


class GeoEngine:
    """
    Geo Score: 0-100 (higher = more favorable geopolitical environment)
    Lower geo scores reduce alpha (geo weight increases after calibration).
    """

    def score(self, sector: str = "") -> float:
        """Score based on active geo events from DB."""
        try:
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            events = execute_query(
                """SELECT event_type, severity, affected_sectors, score_impact
                   FROM geo_events
                   WHERE event_date > ? AND processed = 0
                   ORDER BY event_date DESC LIMIT 20""",
                (cutoff,)
            )
            if not events:
                return 55.0  # Slight positive (no major events)

            risk_total = 0.0
            count      = 0
            for ev in events:
                base_risk = SEVERITY_SCORES.get(ev["severity"], 40)
                # Check sector relevance
                affected  = ev["affected_sectors"] or ""
                relevant  = sector in affected if sector else True
                weight    = 1.5 if relevant else 0.5
                risk_total += base_risk * weight
                count += 1

            avg_risk = risk_total / count if count > 0 else 0.0
            # Convert risk to score (inverted: high risk = low geo score)
            result = round(max(0.0, min(100.0, 100.0 - avg_risk)), 2)
            logger.debug(f"GeoScore[{sector}]={result:.1f} events={count}")
            return result
        except Exception as e:
            logger.error(f"GeoEngine error: {e}")
            return 55.0

    def log_event(self, event_type: str, title: str, severity: str,
                  summary: str = "", affected_sectors: str = "",
                  source_url: str = ""):
        """Manually log a geo-political event."""
        from database.db_manager import execute_write
        execute_write(
            """INSERT INTO geo_events
               (event_type, title, severity, summary, affected_sectors, source_url)
               VALUES (?,?,?,?,?,?)""",
            (event_type, title, severity, summary, affected_sectors, source_url)
        )
        logger.info(f"Geo event logged: [{severity}] {title}")
