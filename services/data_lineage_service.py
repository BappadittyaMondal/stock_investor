"""HFOS v5.0 — Data Lineage Service
Tracks the origin and transformations of every critical data point (scores).
"""
from database.db_manager import execute_write

class DataLineageService:
    def __init__(self):
        pass
        
    def log_lineage(self, stock_id: int, target_table: str, target_row_id: int, 
                    source_system: str, transformation: str, engine: str):
        """Log a data lineage record for audit trailing."""
        execute_write(
            """INSERT INTO data_lineage 
               (stock_id, target_table, target_row_id, source_system, transformation, engine)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (stock_id, target_table, target_row_id, source_system, transformation, engine)
        )
