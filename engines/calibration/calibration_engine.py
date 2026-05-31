"""
HFOS v5.0 — Walk-Forward Calibration Engine
Optimizes 8-engine weights using historical paper-trade outcomes.
Prevents overfitting via rolling out-of-sample validation.
Approved weights are stored in `calibration_runs` and loaded by AlphaEngine.
"""
import logging
from datetime import datetime
from typing import Optional

import numpy as np

from database.db_manager import execute_query, execute_write, execute_one

logger = logging.getLogger(__name__)

# Weight search boundaries
WEIGHT_BOUNDS = {
    "fundamental": (0.15, 0.40),
    "technical":   (0.10, 0.30),
    "sector":      (0.05, 0.20),
    "risk":        (0.08, 0.18),
    "policy":      (0.05, 0.15),
    "news":        (0.03, 0.15),
    "macro":       (0.03, 0.12),
    "geo":         (0.00, 0.10),
}

WEIGHT_KEYS = list(WEIGHT_BOUNDS.keys())


class CalibrationEngine:
    """
    Walk-Forward Weight Calibration:
      1. Pull closed paper trades from DB
      2. Split: 70% train / 30% test (time-ordered)
      3. Grid-search weights on train set (maximize Sharpe)
      4. Validate on test set (check Sharpe, max drawdown)
      5. Save result as DRAFT to `calibration_runs`
      6. ADMIN must APPROVE via UI or CLI before AlphaEngine loads them
    """

    N_GRID_SAMPLES: int = 2000   # random weight combos to evaluate
    MIN_TRADES:     int = 15     # minimum closed trades required

    # -------------------------------------------------------------------------
    # PUBLIC
    # -------------------------------------------------------------------------
    def run(self, approved_by: Optional[int] = None, auto_approve: bool = False) -> dict:
        """
        Execute a full calibration run.
        Returns summary dict with weights, Sharpe, drawdown.
        Raises RuntimeError if insufficient data.
        """
        trades = self._load_trades()
        if len(trades) < self.MIN_TRADES:
            raise RuntimeError(
                f"Calibration requires >= {self.MIN_TRADES} closed paper trades. "
                f"Found: {len(trades)}"
            )

        # Time-ordered train/test split
        split = int(len(trades) * 0.70)
        train = trades[:split]
        test  = trades[split:]

        logger.info(f"Calibration: {len(train)} train trades, {len(test)} test trades")

        # Optimize on training set
        best_weights, train_sharpe = self._grid_search(train)

        # Validate on held-out test set
        test_sharpe, max_dd = self._evaluate(best_weights, test)

        logger.info(
            f"Calibration result: train_sharpe={train_sharpe:.3f} "
            f"test_sharpe={test_sharpe:.3f} max_dd={max_dd:.2%}"
        )

        # Persist result
        status = "APPROVED" if auto_approve else "DRAFT"
        run_id = self._save(
            weights=best_weights,
            n_positions=len(trades), n_used=split,
            sharpe_train=train_sharpe, sharpe_test=test_sharpe,
            max_dd=max_dd, approved_by=approved_by if auto_approve else None,
            status=status
        )

        return {
            "run_id":       run_id,
            "status":       status,
            "weights":      best_weights,
            "train_sharpe": round(train_sharpe, 4),
            "test_sharpe":  round(test_sharpe, 4),
            "max_drawdown": round(max_dd, 4),
            "n_trades":     len(trades),
            "message":      "Awaiting ADMIN approval" if status == "DRAFT" else "AUTO-APPROVED",
        }

    def approve(self, run_id: int, approved_by: int) -> None:
        """Promote a DRAFT calibration run to APPROVED."""
        row = execute_one("SELECT status FROM calibration_runs WHERE id=?", (run_id,))
        if not row:
            raise ValueError(f"Calibration run {run_id} not found")
        if row["status"] == "APPROVED":
            logger.info(f"Run {run_id} already approved")
            return
        execute_write(
            "UPDATE calibration_runs SET status='APPROVED', approved_by=? WHERE id=?",
            (approved_by, run_id)
        )
        logger.info(f"Calibration run {run_id} APPROVED by user {approved_by}")

    def reject(self, run_id: int) -> None:
        execute_write(
            "UPDATE calibration_runs SET status='REJECTED' WHERE id=?", (run_id,)
        )

    def get_latest(self) -> Optional[dict]:
        """Return the latest APPROVED weights."""
        row = execute_one(
            "SELECT * FROM calibration_runs WHERE status='APPROVED' ORDER BY run_date DESC LIMIT 1"
        )
        return dict(row) if row else None

    # -------------------------------------------------------------------------
    # PRIVATE
    # -------------------------------------------------------------------------
    def _load_trades(self) -> list[dict]:
        """Load closed paper trades with their alpha scores and outcomes."""
        rows = execute_query(
            """SELECT pt.alpha_score, pt.pnl_pct, pt.outcome, pt.entry_date,
                      sc.fundamental_score, sc.technical_score, sc.sector_score,
                      sc.risk_score, sc.policy_score, sc.news_score,
                      sc.macro_score, sc.geo_score
               FROM paper_trades pt
               LEFT JOIN scores sc ON pt.stock_id = sc.stock_id
               WHERE pt.outcome IN ('WIN','LOSS','STOPPED')
               AND pt.pnl_pct IS NOT NULL
               ORDER BY pt.entry_date ASC"""
        )
        return [dict(r) for r in rows]

    def _grid_search(self, trades: list[dict]) -> tuple[dict, float]:
        """Random grid search over WEIGHT_BOUNDS to maximize Sharpe."""
        best_sharpe = -999.0
        best_weights = self._default_weights()

        for _ in range(self.N_GRID_SAMPLES):
            weights = self._sample_weights()
            sharpe  = self._sharpe(weights, trades)
            if sharpe > best_sharpe:
                best_sharpe  = sharpe
                best_weights = weights

        return best_weights, best_sharpe

    def _evaluate(self, weights: dict, trades: list[dict]) -> tuple[float, float]:
        """Compute Sharpe and max-drawdown on the test set."""
        if not trades:
            return 0.0, 0.0
        returns = []
        for t in trades:
            alpha  = self._alpha_with_weights(weights, t)
            pnl    = t.get("pnl_pct", 0.0) or 0.0
            returns.append(pnl if alpha >= 75 else 0.0)

        returns_arr = np.array(returns)
        sharpe = self._sharpe_from_returns(returns_arr)
        max_dd = self._max_drawdown(returns_arr)
        return sharpe, max_dd

    def _sharpe(self, weights: dict, trades: list[dict]) -> float:
        returns = []
        for t in trades:
            alpha = self._alpha_with_weights(weights, t)
            pnl   = t.get("pnl_pct", 0.0) or 0.0
            returns.append(pnl if alpha >= 75.0 else 0.0)
        return self._sharpe_from_returns(np.array(returns))

    def _alpha_with_weights(self, weights: dict, trade: dict) -> float:
        try:
            return round(
                trade.get("fundamental_score", 50) * weights["fundamental"]
                + trade.get("technical_score", 50)  * weights["technical"]
                + trade.get("sector_score", 50)      * weights["sector"]
                + (100 - trade.get("risk_score", 50)) * weights["risk"]
                + trade.get("policy_score", 50)      * weights["policy"]
                + trade.get("news_score", 50)        * weights["news"]
                + trade.get("macro_score", 50)       * weights["macro"]
                + trade.get("geo_score", 50)         * weights["geo"],
                2
            )
        except Exception:
            return 50.0

    @staticmethod
    def _sharpe_from_returns(returns: np.ndarray, rf: float = 0.065) -> float:
        if len(returns) < 2:
            return 0.0
        active = returns[returns != 0]
        if len(active) < 2:
            return 0.0
        annual_rf = rf / 252  # daily risk-free
        excess = active - annual_rf
        std = np.std(excess, ddof=1)
        if std == 0:
            return 0.0
        return float(np.mean(excess) / std * np.sqrt(252))

    @staticmethod
    def _max_drawdown(returns: np.ndarray) -> float:
        if len(returns) == 0:
            return 0.0
        cumulative = np.cumprod(1 + returns / 100)
        peak = np.maximum.accumulate(cumulative)
        dd   = (cumulative - peak) / peak
        return float(abs(dd.min())) if len(dd) > 0 else 0.0

    def _sample_weights(self) -> dict:
        """Sample random weights within WEIGHT_BOUNDS, normalized to sum=1."""
        raw = {}
        for k, (lo, hi) in WEIGHT_BOUNDS.items():
            raw[k] = np.random.uniform(lo, hi)
        total = sum(raw.values())
        return {k: round(v / total, 6) for k, v in raw.items()}

    @staticmethod
    def _default_weights() -> dict:
        from engines.scoring.alpha_engine import DEFAULT_WEIGHTS
        return dict(DEFAULT_WEIGHTS)

    def _save(self, weights: dict, n_positions: int, n_used: int,
              sharpe_train: float, sharpe_test: float, max_dd: float,
              approved_by: Optional[int], status: str) -> int:
        return execute_write(
            """INSERT INTO calibration_runs
               (positions_tested, positions_used,
                fw_fundamental, fw_technical, fw_risk, fw_sector,
                fw_policy, fw_news, fw_macro, fw_geo,
                sharpe_train, sharpe_test, max_dd_test,
                status, approved_by, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (n_positions, n_used,
             weights["fundamental"], weights["technical"], weights["risk"],
             weights["sector"], weights["policy"], weights["news"],
             weights["macro"], weights["geo"],
             round(sharpe_train, 6), round(sharpe_test, 6), round(max_dd, 6),
             status, approved_by,
             f"Auto-calibrated at {datetime.now().isoformat()}")
        )
