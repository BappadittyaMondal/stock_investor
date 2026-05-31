"""HFOS v5.0 — Data Health Service
Monitors staleness and detects statistical data anomalies.
"""
import logging
from database.db_manager import execute_query, execute_write

logger = logging.getLogger(__name__)

class DataHealthService:
    def detect_anomalies(self):
        """Scans recent OHLCV and fundamental records for extreme outliers."""
        # Detect Price Gap > 30%
        gaps = execute_query(
            """SELECT a.stock_id, a.date as d1, b.date as d2, a.close as c1, b.close as c2
               FROM ohlcv_cache a
               JOIN ohlcv_cache b ON a.stock_id = b.stock_id AND a.id = b.id + 1
               WHERE a.date >= date('now', '-3 day')
               AND abs((a.close - b.close) / b.close) > 0.30"""
        )
        for g in gaps:
            execute_write(
                "INSERT INTO data_anomalies (stock_id, anomaly_type, description) VALUES (?,?,?)",
                (g["stock_id"], "PRICE_GAP", f"Price gap > 30% between {g['d2']} ({g['c2']}) and {g['d1']} ({g['c1']})")
            )
            
    def check_staleness(self):
        """Checks specific staleness thresholds against DB records."""
        # E.g., Price Data > 1 day old
        # Since this is a service, it would normally be called by the scheduler.
        execute_write(
            """UPDATE data_source_health 
               SET status = 'WARNING', failure_count = failure_count + 1 
               WHERE source = 'NSE_PRICE' 
               AND last_update < datetime('now', '-1 day')"""
        )
        execute_write(
            """UPDATE data_source_health 
               SET status = 'WARNING', failure_count = failure_count + 1 
               WHERE source = 'RSS_NEWS' 
               AND last_update < datetime('now', '-12 hours')"""
        )
        logger.info("Checked data staleness thresholds.")
