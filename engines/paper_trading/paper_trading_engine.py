"""
HFOS v5.0 — Paper Trading Engine
Simulates position entry/exit based on alpha signals without real capital.
Logs outcomes to paper_trades table for walk-forward calibration.
"""
import logging
from datetime import datetime
from typing import Optional

from database.db_manager import execute_write, execute_query, execute_one
from services.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """
    Paper-trades signals from the scanner without committing real capital.
    Provides a live track record for calibration and system validation.

    Lifecycle:
      open_trade()  → records signal entry at market close price
      close_trades() → scans open paper trades and closes those that hit SL/target/expiry
      get_stats()   → returns win rate, avg P&L, Sharpe-like metric
    """

    DEFAULT_HOLDING_DAYS = 60   # auto-close if neither SL nor target hit
    MIN_ALPHA_TO_TRADE   = 75.0

    def __init__(self):
        self.fetcher = DataFetcher()

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────────────────────────────────
    def open_trade(self, stock_id: int, symbol: str, alpha_score: float,
                   signal: str, entry_price: float,
                   stop_loss: float, target_price: float,
                   notes: str = "") -> Optional[int]:
        """
        Open a paper trade. Returns the new paper_trade row id, or None.
        Only opens if alpha >= MIN_ALPHA_TO_TRADE.
        """
        if alpha_score < self.MIN_ALPHA_TO_TRADE:
            logger.debug(f"[Paper] {symbol} alpha={alpha_score:.1f} below threshold — skipped")
            return None

        # Guard: don't open duplicate open paper trade for same stock
        existing = execute_one(
            "SELECT id FROM paper_trades WHERE stock_id=? AND outcome='OPEN'",
            (stock_id,)
        )
        if existing:
            logger.debug(f"[Paper] {symbol} already has an open paper trade — skipped")
            return None

        pid = execute_write(
            """INSERT INTO paper_trades
               (stock_id, alpha_score, signal, entry_price,
                stop_loss, target_price, entry_date, outcome, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (stock_id, round(alpha_score, 2), signal,
             round(entry_price, 2), round(stop_loss, 2),
             round(target_price, 2), datetime.today().strftime("%Y-%m-%d"),
             "OPEN", notes)
        )
        logger.info(f"[Paper] Opened: {symbol} @ ₹{entry_price:.2f} SL=₹{stop_loss:.2f} T=₹{target_price:.2f}")
        return pid

    def close_trades(self) -> dict:
        """
        Evaluate all open paper trades against latest prices.
        Closes positions that hit SL, target, or max holding period.
        Returns summary {closed, wins, losses, stopped}.
        """
        open_trades = execute_query(
            """SELECT pt.*, s.symbol
               FROM paper_trades pt
               JOIN stocks s ON pt.stock_id=s.id
               WHERE pt.outcome='OPEN'"""
        )
        summary = {"closed": 0, "wins": 0, "losses": 0, "stopped": 0, "still_open": 0}

        for trade in open_trades:
            trade = dict(trade)
            symbol = trade["symbol"]
            df = self.fetcher.fetch_ohlcv(symbol, days=5)
            if df is None or df.empty:
                summary["still_open"] += 1
                continue

            ltp          = float(df["close"].iloc[-1])
            entry        = float(trade["entry_price"])
            sl           = float(trade["stop_loss"])
            target       = float(trade["target_price"])
            entry_date   = datetime.strptime(trade["entry_date"], "%Y-%m-%d")
            holding_days = (datetime.today() - entry_date).days

            outcome, exit_price = self._resolve_outcome(
                ltp, entry, sl, target, holding_days
            )

            if outcome == "OPEN":
                summary["still_open"] += 1
                continue

            pnl_pct = round(((exit_price - entry) / entry) * 100, 2)
            execute_write(
                """UPDATE paper_trades
                   SET exit_price=?, exit_date=?, pnl_pct=?, outcome=?
                   WHERE id=?""",
                (round(exit_price, 2), datetime.today().strftime("%Y-%m-%d"),
                 pnl_pct, outcome, trade["id"])
            )
            summary["closed"] += 1
            if outcome == "WIN":
                summary["wins"] += 1
            elif outcome == "LOSS":
                summary["losses"] += 1
            elif outcome == "STOPPED":
                summary["stopped"] += 1
            logger.info(f"[Paper] Closed {symbol}: {outcome} @ ₹{exit_price:.2f} P&L={pnl_pct:.2f}%")

        return summary

    def get_stats(self) -> dict:
        """Return aggregate paper trading performance metrics."""
        rows = execute_query(
            """SELECT outcome, pnl_pct FROM paper_trades
               WHERE outcome IN ('WIN','LOSS','STOPPED') AND pnl_pct IS NOT NULL"""
        )
        if not rows:
            return {"message": "No closed paper trades yet"}

        import numpy as np
        pnl_vals   = [r["pnl_pct"] for r in rows]
        outcomes   = [r["outcome"] for r in rows]
        wins       = outcomes.count("WIN")
        losses     = outcomes.count("LOSS")
        stopped    = outcomes.count("STOPPED")
        total      = len(outcomes)
        win_rate   = round(wins / total * 100, 1) if total else 0
        avg_pnl    = round(float(np.mean(pnl_vals)), 2)
        avg_win    = round(float(np.mean([p for p, o in zip(pnl_vals, outcomes) if o == "WIN"])), 2) if wins else 0
        avg_loss   = round(float(np.mean([p for p, o in zip(pnl_vals, outcomes) if o != "WIN"])), 2) if (losses + stopped) else 0
        std_pnl    = float(np.std(pnl_vals, ddof=1)) if total > 1 else 0.0
        sharpe_est = round((avg_pnl / std_pnl) if std_pnl > 0 else 0.0, 3)

        return {
            "total_trades": total,
            "wins":         wins,
            "losses":       losses,
            "stopped":      stopped,
            "win_rate_pct": win_rate,
            "avg_pnl_pct":  avg_pnl,
            "avg_win_pct":  avg_win,
            "avg_loss_pct": avg_loss,
            "sharpe_est":   sharpe_est,
        }

    def get_open_trades(self) -> list[dict]:
        rows = execute_query(
            """SELECT pt.*, s.symbol, s.sector
               FROM paper_trades pt JOIN stocks s ON pt.stock_id=s.id
               WHERE pt.outcome='OPEN' ORDER BY pt.entry_date DESC"""
        )
        return [dict(r) for r in rows]

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────────────────────────────────
    def _resolve_outcome(self, ltp: float, entry: float,
                          sl: float, target: float,
                          holding_days: int) -> tuple[str, float]:
        """Determine if trade should close and with what outcome."""
        if ltp <= sl:
            return "STOPPED", sl
        if ltp >= target:
            return "WIN", target
        if holding_days >= self.DEFAULT_HOLDING_DAYS:
            # Force-close at LTP; count win/loss by direction
            outcome = "WIN" if ltp > entry else "LOSS"
            return outcome, ltp
        return "OPEN", ltp
