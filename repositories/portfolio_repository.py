"""
HFOS v5.0 — Portfolio Repository
"""
import logging
from typing import Optional
from database.db_manager import execute_query, execute_one, execute_write
from schemas.validators import PortfolioCreate

logger = logging.getLogger(__name__)


class PortfolioRepository:
    def get_active(self) -> list[dict]:
        return [dict(r) for r in execute_query(
            """SELECT p.*, s.symbol, s.name, s.sector
               FROM portfolio p JOIN stocks s ON p.stock_id=s.id
               WHERE p.is_active=1 ORDER BY p.position_size DESC"""
        )]

    def get_by_id(self, position_id: int) -> Optional[dict]:
        row = execute_one(
            "SELECT p.*, s.symbol, s.name FROM portfolio p JOIN stocks s ON p.stock_id=s.id WHERE p.id=?",
            (position_id,)
        )
        return dict(row) if row else None

    def get_by_stock(self, stock_id: int) -> Optional[dict]:
        row = execute_one(
            "SELECT * FROM portfolio WHERE stock_id=? AND is_active=1", (stock_id,)
        )
        return dict(row) if row else None

    def create(self, data: PortfolioCreate) -> int:
        return execute_write(
            """INSERT INTO portfolio (stock_id,quantity,avg_cost,entry_date,
               stop_loss,target_price,position_size,tier,strategy,notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (data.stock_id, data.quantity, data.avg_cost, data.entry_date,
             data.stop_loss, data.target_price, data.position_size,
             data.tier, data.strategy, data.notes)
        )

    def close_position(self, position_id: int, exit_price: float,
                       exit_date: str, exit_reason: str) -> None:
        execute_write(
            """UPDATE portfolio SET is_active=0, exit_price=?, exit_date=?,
               exit_reason=?, updated_at=datetime('now') WHERE id=?""",
            (exit_price, exit_date, exit_reason, position_id)
        )

    def update_stop_loss(self, position_id: int, new_sl: float) -> None:
        execute_write(
            "UPDATE portfolio SET stop_loss=?, updated_at=datetime('now') WHERE id=?",
            (new_sl, position_id)
        )

    def get_closed(self, limit: int = 100) -> list[dict]:
        return [dict(r) for r in execute_query(
            """SELECT p.*, s.symbol, s.name FROM portfolio p
               JOIN stocks s ON p.stock_id=s.id
               WHERE p.is_active=0 ORDER BY p.exit_date DESC LIMIT ?""",
            (limit,)
        )]

    def count_active(self) -> int:
        row = execute_one("SELECT COUNT(*) AS cnt FROM portfolio WHERE is_active=1")
        return row["cnt"] if row else 0

    def record_transaction(self, stock_id: int, portfolio_id: Optional[int],
                           txn_type: str, quantity: int, price: float,
                           txn_date: str, brokerage: float = 0.0) -> int:
        stt = price * quantity * 0.001 if txn_type == "SELL" else price * quantity * 0.0001
        net = price * quantity + brokerage + stt
        if txn_type == "BUY":
            net = -(price * quantity + brokerage + stt)
        return execute_write(
            """INSERT INTO transactions(portfolio_id,stock_id,txn_type,quantity,
               price,brokerage,stt,net_amount,txn_date)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (portfolio_id, stock_id, txn_type, quantity, price,
             brokerage, round(stt, 2), round(abs(net), 2), txn_date)
        )
