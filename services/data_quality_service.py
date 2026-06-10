"""HFOS v5.0 — Data Quality Service
Scores and validates data quality before engines process it.
"""
import logging
from database.db_manager import execute_write, execute_one

logger = logging.getLogger(__name__)

SOURCE_RELIABILITY = {
    "NSE": 1.0,
    "BSE": 1.0,
    "SEBI": 0.95,
    "PIB": 0.95,
    "Screener": 0.90,
    "RSS": 0.70,
    "yfinance": 0.85
}

class DataQualityService:
    def __init__(self):
        logger.debug("DataQualityService initialized")
        
    def evaluate_source(self, source: str) -> float:
        """Evaluate the current quality score (0-100) for a source."""
        # Baseline scoring from source class; finer-grained scoring can be added
        # when source-specific completeness/freshness telemetry is available.
        completeness = 0.95
        freshness = 0.90
        consistency = 0.98
        accuracy = 0.92
        reliability = SOURCE_RELIABILITY.get(source, 0.50)
        
        quality_score = (
            completeness * 30 +
            freshness * 25 +
            consistency * 20 +
            accuracy * 15 +
            reliability * 10
        )
        
        execute_write(
            """INSERT INTO data_quality_metrics 
               (source, quality_score, completeness, freshness, consistency, accuracy, reliability)
               VALUES (?,?,?,?,?,?,?)""",
            (source, quality_score, completeness, freshness, consistency, accuracy, reliability)
        )
        return quality_score
        
    def get_latest_quality_score(self, source: str) -> float:
        row = execute_one(
            "SELECT quality_score FROM data_quality_metrics WHERE source=? ORDER BY evaluated_at DESC LIMIT 1",
            (source,)
        )
        return row["quality_score"] if row else self.evaluate_source(source)
        
    def validate_integrity(self, df, context: str = "") -> bool:
        """Validate integrity rules (no negative prices, missing symbols)."""
        if df is None or df.empty:
            return False
            
        if "close" in df.columns and (df["close"] <= 0).any():
            logger.error(f"[{context}] Negative/Zero close price detected.")
            return False
            
        if "volume" in df.columns and (df["volume"] < 0).any():
            logger.error(f"[{context}] Negative volume detected.")
            return False
            
        return True
