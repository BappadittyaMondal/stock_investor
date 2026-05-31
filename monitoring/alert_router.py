"""HFOS v5.0 — Alert Router"""
import logging
from services.alert_service import AlertService

logger = logging.getLogger(__name__)

class AlertRouter:
    """Centralizes and routes all system alerts by priority."""
    
    @staticmethod
    def route(category: str, message: str, priority: str = "P3"):
        """
        P1 Critical: Database down, feed failure, security breach
        P2 High: Data anomaly, AI quota warning
        P3 Medium: Portfolio threshold breached
        P4 Low: Informational
        """
        logger.info(f"Routing {priority} alert [{category}]: {message}")
        
        # Translate to AlertService priorities (CRITICAL, HIGH, MEDIUM, LOW)
        p_map = {"P1": "CRITICAL", "P2": "HIGH", "P3": "MEDIUM", "P4": "LOW"}
        sys_priority = p_map.get(priority, "MEDIUM")
        
        AlertService().send(
            message=f"[{category}] {message}",
            priority=sys_priority,
            alert_type="SYSTEM_ALERT"
        )
