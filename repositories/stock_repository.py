"""
HFOS v5.0 — Stock Repository
Data access layer for stocks table. No SQL in services or UI.
"""
import logging
from typing import Optional
from database.db_manager import execute_query, execute_one, execute_write, execute_many
from schemas.validators import StockCreate

logger = logging.getLogger(__name__)


class StockRepository:
    def get_all(self, active_only: bool = True) -> list[dict]:
        sql = "SELECT * FROM stocks"
        if active_only:
            sql += " WHERE is_active=1"
        sql += " ORDER BY market_cap_cr DESC NULLS LAST"
        return [dict(r) for r in execute_query(sql)]

    def get_by_symbol(self, symbol: str) -> Optional[dict]:
        row = execute_one(
            "SELECT * FROM stocks WHERE symbol=? COLLATE NOCASE", (symbol,)
        )
        return dict(row) if row else None

    def get_by_id(self, stock_id: int) -> Optional[dict]:
        row = execute_one("SELECT * FROM stocks WHERE id=?", (stock_id,))
        return dict(row) if row else None

    def get_by_sector(self, sector: str) -> list[dict]:
        return [dict(r) for r in execute_query(
            "SELECT * FROM stocks WHERE sector=? AND is_active=1 ORDER BY market_cap_cr DESC",
            (sector,)
        )]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        q = f"%{query.upper()}%"
        return [dict(r) for r in execute_query(
            "SELECT * FROM stocks WHERE (symbol LIKE ? OR name LIKE ?) AND is_active=1 LIMIT ?",
            (q, f"%{query}%", limit)
        )]

    def create(self, data: StockCreate) -> int:
        return execute_write(
            """INSERT INTO stocks (symbol,name,exchange,sector,industry,
               market_cap_cr,isin,face_value,is_active)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(symbol) DO NOTHING""",
            (data.symbol, data.name, data.exchange, data.sector,
             data.industry, data.market_cap_cr, data.isin,
             data.face_value, int(data.is_active))
        )

    def bulk_upsert(self, stocks: list[dict]) -> int:
        rows = [
            (s["symbol"], s["name"], s.get("exchange","NSE"), s.get("sector"),
             s.get("market_cap_cr"), s.get("isin"), s.get("avg_daily_vol",0))
            for s in stocks
        ]
        return execute_many(
            """INSERT INTO stocks(symbol,name,exchange,sector,market_cap_cr,isin,avg_daily_vol)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(symbol) DO UPDATE SET
               name=excluded.name, sector=excluded.sector,
               market_cap_cr=excluded.market_cap_cr,
               avg_daily_vol=excluded.avg_daily_vol,
               updated_at=datetime('now')""",
            rows
        )

    def update_flags(self, symbol: str, asm: int = 0, gsm: int = 0,
                     pledge_pct: float = 0.0) -> None:
        execute_write(
            "UPDATE stocks SET asm_flag=?, gsm_flag=?, pledge_pct=?, updated_at=datetime('now') WHERE symbol=?",
            (asm, gsm, pledge_pct, symbol)
        )

    def deactivate(self, symbol: str) -> None:
        execute_write("UPDATE stocks SET is_active=0 WHERE symbol=?", (symbol,))

    def get_asm_gsm_list(self) -> list[dict]:
        return [dict(r) for r in execute_query(
            "SELECT * FROM stocks WHERE asm_flag=1 OR gsm_flag=1 ORDER BY symbol"
        )]

    def get_unique_sectors(self) -> list[str]:
        rows = execute_query(
            "SELECT DISTINCT sector FROM stocks WHERE sector IS NOT NULL AND is_active=1 ORDER BY sector"
        )
        return [r["sector"] for r in rows]
