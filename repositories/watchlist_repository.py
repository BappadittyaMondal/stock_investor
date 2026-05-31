"""
HFOS v5.0 — Watchlist Repository
"""
from database.db_manager import execute_query, execute_one, execute_write
from typing import Optional


class WatchlistRepository:
    TIERS = ("HIGH_CONVICTION", "EMERGING_LEADERS",
              "POLICY_BENEFICIARIES", "SPECULATIVE", "TURNAROUND")

    def get_by_tier(self, tier: str) -> list[dict]:
        return [dict(r) for r in execute_query(
            """SELECT w.*, s.symbol, s.name, s.sector, s.market_cap_cr
               FROM watchlists w JOIN stocks s ON w.stock_id=s.id
               WHERE w.tier=? ORDER BY w.added_at DESC""",
            (tier,)
        )]

    def get_all(self) -> dict[str, list[dict]]:
        return {tier: self.get_by_tier(tier) for tier in self.TIERS}

    def add(self, name: str, stock_id: int, tier: str,
            added_by: Optional[int] = None, notes: str = "") -> int:
        if tier not in self.TIERS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of {self.TIERS}")
        return execute_write(
            "INSERT OR IGNORE INTO watchlists(name,stock_id,tier,added_by,notes) VALUES(?,?,?,?,?)",
            (name, stock_id, tier, added_by, notes)
        )

    def remove(self, stock_id: int, tier: str) -> None:
        execute_write(
            "DELETE FROM watchlists WHERE stock_id=? AND tier=?", (stock_id, tier)
        )

    def is_in_watchlist(self, stock_id: int) -> bool:
        row = execute_one("SELECT 1 FROM watchlists WHERE stock_id=?", (stock_id,))
        return row is not None

    def promote(self, stock_id: int, from_tier: str, to_tier: str,
                added_by: Optional[int] = None) -> None:
        """Move stock from one tier to another."""
        self.remove(stock_id, from_tier)
        self.add(stock_id=stock_id, name=to_tier, tier=to_tier, added_by=added_by)

    def count_by_tier(self) -> dict[str, int]:
        rows = execute_query(
            "SELECT tier, COUNT(*) AS cnt FROM watchlists GROUP BY tier"
        )
        return {r["tier"]: r["cnt"] for r in rows}
