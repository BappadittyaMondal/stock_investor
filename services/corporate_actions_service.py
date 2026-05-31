"""HFOS v5.0 — Corporate Actions Service
Handles adjustments for splits, bonuses, and dividends across historical records.
"""
import logging
from database.db_manager import execute_write

logger = logging.getLogger(__name__)

class CorporateActionsService:
    def apply_split(self, stock_id: int, old_ratio: float, new_ratio: float):
        """Apply stock split adjustments to OHLCV and Portfolio."""
        multiplier = old_ratio / new_ratio  # e.g., 2:1 split -> 0.5
        qty_multiplier = new_ratio / old_ratio
        
        # 1. Adjust OHLCV history
        execute_write(
            """UPDATE ohlcv_cache SET 
               open = open * ?, high = high * ?, low = low * ?, close = close * ?,
               volume = volume * ?
               WHERE stock_id = ?""",
            (multiplier, multiplier, multiplier, multiplier, qty_multiplier, stock_id)
        )
        
        # 2. Adjust Portfolio Avg Cost & Target/SL
        execute_write(
            """UPDATE portfolio SET 
               avg_cost = avg_cost * ?, stop_loss = stop_loss * ?, target_price = target_price * ?,
               quantity = quantity * ?
               WHERE stock_id = ? AND is_active = 1""",
            (multiplier, multiplier, multiplier, qty_multiplier, stock_id)
        )
        
        # 3. Adjust Paper Trades
        execute_write(
            """UPDATE paper_trades SET 
               entry_price = entry_price * ?, stop_loss = stop_loss * ?, target_price = target_price * ?,
               exit_price = exit_price * ?
               WHERE stock_id = ? AND outcome = 'OPEN'""",
            (multiplier, multiplier, multiplier, multiplier, stock_id)
        )
        
        logger.info(f"Applied corporate action (SPLIT {old_ratio}:{new_ratio}) for stock {stock_id}")
