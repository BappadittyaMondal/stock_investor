"""HFOS v5.0 — Metrics Service"""
from database.db_manager import execute_write

class MetricsService:
    @staticmethod
    def record_metric(name: str, value: float, tags: str = ""):
        """Records a system metric."""
        execute_write(
            "INSERT INTO system_metrics (metric_name, metric_value, tags) VALUES (?,?,?)",
            (name, value, tags)
        )
