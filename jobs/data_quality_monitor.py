"""HFOS v5.0 — Data Quality Monitor Job"""
import logging
from services.data_health_service import DataHealthService
from services.alert_service import AlertService
from database.db_manager import execute_query

logger = logging.getLogger(__name__)

def job_data_quality_monitor():
    """Runs data anomaly detection and stale checking."""
    logger.info("=== DATA QUALITY MONITOR START ===")
    try:
        health = DataHealthService()
        health.detect_anomalies()
        health.check_staleness()
        
        # Pull critical anomalies to alert
        anomalies = execute_query("SELECT * FROM data_anomalies WHERE resolved=0 AND detected_at >= datetime('now', '-1 hour')")
        if anomalies:
            AlertService().send(
                f"⚠️ Data Anomaly Detected: {len(anomalies)} anomalies found.", 
                priority="HIGH", alert_type="DATA_QUALITY"
            )
        logger.info("Data Quality Monitor complete.")
    except Exception as e:
        logger.error(f"Data Quality Monitor failed: {e}")
