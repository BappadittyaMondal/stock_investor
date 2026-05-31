"""HFOS v5.0 — Telemetry Service"""
from database.db_manager import execute_write

class TelemetryService:
    @staticmethod
    def record_action(action: str, result: str, duration_ms: float, status: str = "SUCCESS"):
        """Record system action telemetry."""
        execute_write(
            "INSERT INTO telemetry_logs (action_name, result, duration_ms, status) VALUES (?,?,?,?)",
            (action, result, duration_ms, status)
        )
