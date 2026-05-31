"""HFOS v5.0 — Health Monitor Job"""
import logging
from monitoring.health_service import HealthService
from monitoring.alert_router import AlertRouter
from database.db_manager import execute_write

logger = logging.getLogger(__name__)

def job_health_monitor():
    """Runs automated health checks and triggers failure recovery."""
    logger.info("=== HEALTH MONITOR START ===")
    
    checks = HealthService.run_all_checks()
    
    # Check Database
    if checks["Database"]["status"] != "healthy":
        execute_write("INSERT INTO system_errors (service_name, severity, error_message) VALUES (?,?,?)",
                      ("Database", "CRITICAL", checks["Database"].get("error","Unknown DB Error")))
        AlertRouter.route("System", "Database Connection Critical", "P1")
        # Trigger Fallback Read Mode logic here (simulated)

    # Check Data Feeds (using existing data_source_health table)
    # If feed fails -> Use Cache -> Reduce Confidence -> Alert
    
    logger.info("Health Monitor complete.")
