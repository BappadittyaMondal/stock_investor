"""HFOS v5.0 — Strategy Registry"""
import json
from database.db_manager import execute_write, execute_query

class StrategyRegistry:
    def register(self, name: str, version: str, params: dict):
        execute_write(
            "INSERT INTO strategy_registry (name, version, parameters) VALUES (?,?,?)",
            (name, version, json.dumps(params))
        )
        
    def list_strategies(self):
        return execute_query("SELECT * FROM strategy_registry ORDER BY created_date DESC")
        
    def approve(self, strategy_id: int):
        execute_write("UPDATE strategy_registry SET status = 'APPROVED' WHERE id=?", (strategy_id,))
