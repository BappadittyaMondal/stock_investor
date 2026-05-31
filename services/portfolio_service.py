"""
HFOS v5.0 — Portfolio Service
Position sizing, XIRR, P&L, correlation controls, tax logic.
"""
import logging
from datetime import date, datetime
from typing import Optional
from scipy.optimize import brentq

from database.db_manager import execute_one, execute_query
from config.settings import (
    CAPITAL_INR, MAX_PORTFOLIO_POSITIONS,
    MAX_POSITION_SIZE_PCT, MAX_SECTOR_EXPOSURE_PCT,
    DEFAULT_STOP_LOSS_PCT, DEFAULT_TARGET_MULTIPLIER
)

logger = logging.getLogger(__name__)


class PortfolioService:
    """
    Portfolio management: sizing, XIRR, P&L, tax, sector controls.
    """

    # -------------------------------------------------------------------------
    # Position Sizing
    # -------------------------------------------------------------------------
    def calculate_position_size(
        self,
        alpha_score: float,
        current_price: float,
        stop_loss: float,
        risk_per_trade_pct: float = 1.0,
    ) -> dict:
        """
        Kelly-inspired position sizing with risk-per-trade cap.
        Returns dict with: shares, invested_inr, position_pct, stop_loss, target
        """
        if stop_loss >= current_price:
            raise ValueError("stop_loss must be below current_price")

        # Risk amount per trade = 1% of capital (configurable)
        risk_amount = CAPITAL_INR * (risk_per_trade_pct / 100.0)
        risk_per_share = current_price - stop_loss

        if risk_per_share <= 0:
            raise ValueError("Invalid SL — risk_per_share <= 0")

        # Base shares from risk
        shares = int(risk_amount / risk_per_share)

        # Apply alpha-weighted position scaling (higher alpha → larger position)
        alpha_multiplier = 0.5 + (alpha_score - 75.0) / 100.0  # 0.5x to 0.75x at 75-100
        alpha_multiplier = max(0.5, min(1.0, alpha_multiplier))
        shares = int(shares * alpha_multiplier)

        invested = shares * current_price
        position_pct = (invested / CAPITAL_INR) * 100.0

        # Hard cap: max position size
        if position_pct > MAX_POSITION_SIZE_PCT:
            position_pct = MAX_POSITION_SIZE_PCT
            invested     = CAPITAL_INR * MAX_POSITION_SIZE_PCT / 100.0
            shares       = int(invested / current_price)

        target = current_price + (current_price - stop_loss) * DEFAULT_TARGET_MULTIPLIER

        return {
            "shares":       shares,
            "invested_inr": round(invested, 2),
            "position_pct": round(position_pct, 2),
            "stop_loss":    round(stop_loss, 2),
            "target":       round(target, 2),
            "risk_reward":  round(DEFAULT_TARGET_MULTIPLIER, 1),
        }

    def suggest_stop_loss(self, entry_price: float, atr: Optional[float] = None) -> float:
        """2x ATR below entry, or DEFAULT_STOP_LOSS_PCT if ATR unavailable."""
        if atr and atr > 0:
            sl = entry_price - (2.0 * atr)
        else:
            sl = entry_price * (1 - DEFAULT_STOP_LOSS_PCT / 100.0)
        return round(max(sl, entry_price * 0.80), 2)  # never more than 20% below

    # -------------------------------------------------------------------------
    # Portfolio State
    # -------------------------------------------------------------------------
    def get_active_positions(self) -> list[dict]:
        rows = execute_query(
            """SELECT p.*, s.symbol, s.name, s.sector,
                      s.asm_flag, s.gsm_flag, s.pledge_pct
               FROM portfolio p
               JOIN stocks s ON p.stock_id = s.id
               WHERE p.is_active=1
               ORDER BY p.position_size DESC""",
        )
        return [dict(r) for r in rows]

    def get_sector_exposure(self) -> dict[str, float]:
        """Return {sector: pct_of_portfolio} for active positions."""
        positions = self.get_active_positions()
        if not positions:
            return {}
        total_invested = sum(
            p["quantity"] * p["avg_cost"] for p in positions
        )
        if total_invested <= 0:
            return {}
        sector_map: dict[str, float] = {}
        for p in positions:
            sector = p.get("sector") or "Unknown"
            invested = p["quantity"] * p["avg_cost"]
            sector_map[sector] = sector_map.get(sector, 0.0) + invested
        return {k: round((v / total_invested) * 100, 2) for k, v in sector_map.items()}

    def sector_has_capacity(self, sector: str) -> tuple[bool, float]:
        """True if sector is below MAX_SECTOR_EXPOSURE_PCT."""
        exposure = self.get_sector_exposure()
        current  = exposure.get(sector, 0.0)
        return current < MAX_SECTOR_EXPOSURE_PCT, current

    def position_count_ok(self) -> bool:
        row = execute_one("SELECT COUNT(*) AS cnt FROM portfolio WHERE is_active=1")
        return (row["cnt"] if row else 0) < MAX_PORTFOLIO_POSITIONS

    # -------------------------------------------------------------------------
    # P&L and XIRR
    # -------------------------------------------------------------------------
    def calculate_pnl(self, positions: list[dict], current_prices: dict[str, float]) -> dict:
        """
        Args:
            positions: list of active portfolio rows
            current_prices: {symbol: last_close}
        Returns: {total_invested, current_value, unrealised_pnl, unrealised_pct}
        """
        total_invested = 0.0
        current_value  = 0.0
        for p in positions:
            sym   = p["symbol"]
            ltp   = current_prices.get(sym, p["avg_cost"])
            inv   = p["quantity"] * p["avg_cost"]
            curr  = p["quantity"] * ltp
            total_invested += inv
            current_value  += curr

        unrealised = current_value - total_invested
        pct = (unrealised / total_invested * 100) if total_invested > 0 else 0.0
        return {
            "total_invested":  round(total_invested, 2),
            "current_value":   round(current_value, 2),
            "unrealised_pnl":  round(unrealised, 2),
            "unrealised_pct":  round(pct, 2),
        }

    def calculate_xirr(self, stock_id: Optional[int] = None) -> Optional[float]:
        """
        XIRR calculation using Newton-Raphson / Brent's method.
        Uses transactions table for cash flows.
        """
        try:
            if stock_id:
                rows = execute_query(
                    "SELECT txn_date, net_amount, txn_type FROM transactions WHERE stock_id=? ORDER BY txn_date",
                    (stock_id,)
                )
            else:
                rows = execute_query(
                    "SELECT txn_date, net_amount, txn_type FROM transactions ORDER BY txn_date"
                )
            if not rows or len(rows) < 2:
                return None

            cashflows = []
            dates     = []
            for r in rows:
                amount = r["net_amount"]
                # BUY = negative cashflow (money out), SELL/DIVIDEND = positive
                if r["txn_type"] == "BUY":
                    cashflows.append(-abs(amount))
                else:
                    cashflows.append(abs(amount))
                dates.append(datetime.strptime(r["txn_date"], "%Y-%m-%d").date())

            return self._xirr(cashflows, dates)
        except Exception as e:
            logger.warning(f"XIRR calculation failed: {e}")
            return None

    # -------------------------------------------------------------------------
    # Tax Logic
    # -------------------------------------------------------------------------
    def estimate_tax(self, buy_date: str, sell_date: str,
                     buy_price: float, sell_price: float, quantity: int) -> dict:
        """
        Indian equity tax:
          STCG (< 12 months): 20% (post Budget 2024)
          LTCG (> 12 months): 12.5% above Rs 1.25L threshold
        """
        bd = datetime.strptime(buy_date, "%Y-%m-%d").date()
        sd = datetime.strptime(sell_date, "%Y-%m-%d").date()
        holding_days = (sd - bd).days
        gain = (sell_price - buy_price) * quantity

        if holding_days < 365:
            tax_rate = 0.20  # STCG post-Budget 2024
            tax_type = "STCG"
        else:
            tax_rate = 0.125  # LTCG post-Budget 2024
            tax_type = "LTCG"
            # Rs 1.25L LTCG exemption
            if gain > 0:
                gain = max(0.0, gain - 125000)

        tax = max(0.0, gain * tax_rate)
        return {
            "holding_days": holding_days,
            "tax_type":     tax_type,
            "gain":         round(gain, 2),
            "tax_rate_pct": tax_rate * 100,
            "estimated_tax":round(tax, 2),
            "net_gain":     round(gain - tax, 2),
        }

    # -------------------------------------------------------------------------
    # Private
    # -------------------------------------------------------------------------
    def _xirr(self, cashflows: list[float], dates: list[date]) -> Optional[float]:
        """Internal XIRR via Brent's method."""
        if not cashflows or len(cashflows) < 2:
            return None
        if sum(cashflows) == 0:
            return 0.0

        origin = dates[0]
        day_fracs = [(d - origin).days / 365.0 for d in dates]

        def npv(rate: float) -> float:
            return sum(cf / ((1 + rate) ** t) for cf, t in zip(cashflows, day_fracs))

        try:
            return round(brentq(npv, -0.999, 100.0, xtol=1e-8, maxiter=500), 4)
        except ValueError:
            return None
