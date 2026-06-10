"""
HFOS v5.0 — Alpha Engine (8-Engine Composite Scorer)
UPGRADED:
  - 8-engine support (fundamental, technical, sector, risk, policy, news, macro, geo)
  - Risk score correctly inverted
  - Dynamic weight loading from approved calibration_runs
  - Hard portfolio gates
  - Walk-forward calibration support
"""
import logging
from typing import Optional

from database.db_manager import execute_one
from schemas.validators import DataValidator
from services.data_quality_service import DataQualityService
from services.data_lineage_service import DataLineageService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default weights (sum = 1.00)
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS: dict[str, float] = {
    "fundamental": 0.25,
    "technical":   0.20,
    "sector":      0.15,
    "risk":        0.12,   # applied as (100 - risk_score)
    "policy":      0.10,
    "news":        0.10,
    "macro":       0.08,
    "geo":         0.00,   # activated after geo engine calibrated
}

# ---------------------------------------------------------------------------
# Score thresholds → (signal, confidence)
# ---------------------------------------------------------------------------
SCORE_THRESHOLDS: dict[int, tuple[str, str]] = {
    90: ("STRONG_BUY",  "INSTITUTIONAL"),
    80: ("BUY",         "HIGH_CONVICTION"),
    70: ("ACCUMULATE",  "WATCHLIST"),
    50: ("WATCH",       "SPECULATIVE"),
    0:  ("REJECT",      "AVOID"),
}

# ---------------------------------------------------------------------------
# Hard portfolio eligibility gates
# ---------------------------------------------------------------------------
GATES: dict[str, float] = {
    "MIN_ALPHA_SCORE":       75.0,
    "MAX_SECTOR_EXPOSURE":   25.0,
    "MAX_POSITION_SIZE":     10.0,
    "MIN_AVG_DAILY_VOLUME":  500_000,
    "MAX_PLEDGE_PCT":        40.0,
    "MIN_MARKET_CAP_CR":     200.0,
}


class AlphaEngine:
    """Composite Alpha Score — 8-engine weighted formula."""

    WEIGHTS_VERSION = "v5.0"

    def __init__(self, db_path: Optional[str] = None, load_calibrated: bool = True):
        self.weights = dict(DEFAULT_WEIGHTS)
        if load_calibrated:
            self._load_approved_weights()

    # -------------------------------------------------------------------------
    # PUBLIC
    # -------------------------------------------------------------------------
    def calculate(self, scores: dict) -> float:
        """
        Calculate composite alpha score.
        Expected keys: fundamental_score, technical_score, risk_score,
                       policy_score, macro_score, sector_score, news_score,
                       geo_score (optional, defaults to 50)
        Returns 0-100 float.
        """
        required = {"fundamental_score", "technical_score", "sector_score",
                    "risk_score", "policy_score", "news_score", "macro_score"}
        missing = required - set(scores.keys())
        if missing:
            raise ValueError(f"AlphaEngine.calculate(): missing score keys: {missing}")

        # Validate only recognised score fields (not gate-check fields)
        _score_keys = {k for k in scores if k.endswith("_score")}
        for key in _score_keys:
            scores[key] = DataValidator.validate_score(scores[key], key)

        w = self.weights
        geo = scores.get("geo_score", 50.0)

        alpha = (
            scores["fundamental_score"] * w["fundamental"]
            + scores["technical_score"]  * w["technical"]
            + scores["sector_score"]     * w["sector"]
            + (100.0 - scores["risk_score"]) * w["risk"]   # INVERTED
            + scores["policy_score"]     * w["policy"]
            + scores["news_score"]       * w["news"]
            + scores["macro_score"]      * w["macro"]
            + geo                        * w["geo"]
        )
        return round(max(0.0, min(100.0, alpha)), 2)

    def classify(self, alpha: float) -> tuple[str, str]:
        """Returns (signal, confidence) for a given alpha score."""
        for threshold in sorted(SCORE_THRESHOLDS.keys(), reverse=True):
            if alpha >= threshold:
                return SCORE_THRESHOLDS[threshold]
        return "REJECT", "AVOID"

    def bucket(self, alpha: float) -> str:
        if alpha >= 90: return "90-100"
        if alpha >= 80: return "80-89"
        if alpha >= 70: return "70-79"
        if alpha >= 60: return "60-69"
        return "Below-60"

    def is_portfolio_eligible(
        self,
        stock_data: dict,
        alpha: float,
        current_sector_exposure: float,
    ) -> tuple[bool, str]:
        """All gates must pass before any position entry."""
        if stock_data.get("asm_flag"):
            return False, "ASM flag active — excluded from portfolio"
        if stock_data.get("gsm_flag"):
            return False, "GSM flag active — excluded from portfolio"
        pledge = stock_data.get("pledge_pct", 0.0) or 0.0
        if pledge > GATES["MAX_PLEDGE_PCT"]:
            return False, f"Pledge {pledge:.1f}% > max {GATES['MAX_PLEDGE_PCT']:.0f}%"
        if alpha < GATES["MIN_ALPHA_SCORE"]:
            return False, f"Alpha {alpha:.1f} < minimum {GATES['MIN_ALPHA_SCORE']:.0f}"
        if current_sector_exposure >= GATES["MAX_SECTOR_EXPOSURE"]:
            return False, f"Sector at {current_sector_exposure:.1f}% — limit {GATES['MAX_SECTOR_EXPOSURE']:.0f}%"
        avg_vol = stock_data.get("avg_daily_vol", 0) or 0
        if avg_vol < GATES["MIN_AVG_DAILY_VOLUME"]:
            return False, f"Volume {avg_vol:,} < min {GATES['MIN_AVG_DAILY_VOLUME']:,}"
        mktcap = stock_data.get("market_cap_cr", 999.0) or 999.0
        if mktcap < GATES["MIN_MARKET_CAP_CR"]:
            return False, f"Market cap ₹{mktcap:.0f}Cr < ₹{GATES['MIN_MARKET_CAP_CR']:.0f}Cr"
        return True, "ELIGIBLE"

    def score_batch(self, stocks_scores: list[dict]) -> list[dict]:
        """Score multiple stocks and return enriched records."""
        results = []
        dq_svc = DataQualityService()
        dl_svc = DataLineageService()
        
        for s in stocks_scores:
            try:
                # 1. Check Data Quality (using a generic source or primary data source)
                # In a real system, you'd aggregate the quality of all inputs.
                q_score = dq_svc.get_latest_quality_score("Screener")
                
                # 2. Calculate Alpha
                alpha = self.calculate(s)
                signal, confidence = self.classify(alpha)
                
                # 3. Apply Quality Penalties
                if q_score < 50:
                    signal = "REJECT"
                    confidence = "AVOID"
                    logger.warning(f"[{s.get('symbol','?')}] Signal blocked due to Critical Data Quality ({q_score:.1f})")
                elif q_score < 70:
                    confidence = "SPECULATIVE" # Downgrade confidence
                    logger.info(f"[{s.get('symbol','?')}] Confidence downgraded due to Warning Data Quality ({q_score:.1f})")

                result = {
                    **s,
                    "alpha_score": alpha,
                    "signal": signal,
                    "confidence": confidence,
                    "bucket": self.bucket(alpha),
                    "weight_version": self.WEIGHTS_VERSION,
                }
                results.append(result)
                
                # 4. Log lineage for the alpha save event
                dl_svc.log_lineage(
                    stock_id=s.get("stock_id", 0),
                    target_table="scores",
                    target_row_id=0, 
                    source_system="Multi-Engine",
                    transformation=f"WeightVersion: {self.WEIGHTS_VERSION}",
                    engine="AlphaEngine"
                )
                
            except Exception as e:
                logger.warning(f"Failed to score stock {s.get('symbol','?')}: {e}")
        return results

    # -------------------------------------------------------------------------
    # PRIVATE
    # -------------------------------------------------------------------------
    def _load_approved_weights(self):
        """Load latest APPROVED calibration weights from DB if available."""
        try:
            row = execute_one(
                """SELECT fw_fundamental, fw_technical, fw_risk, fw_sector,
                          fw_policy, fw_news, fw_macro, fw_geo
                   FROM calibration_runs
                   WHERE status = 'APPROVED'
                   ORDER BY run_date DESC LIMIT 1"""
            )
            if row:
                keys = ["fundamental", "technical", "risk", "sector",
                        "policy", "news", "macro", "geo"]
                loaded = dict(zip(keys, row))
                total = sum(loaded.values())
                if abs(total - 1.0) < 0.02:
                    self.weights.update(loaded)
                    logger.info(f"Loaded calibrated weights (sum={total:.4f})")
                else:
                    logger.warning(f"Calibrated weights sum={total:.4f} — rejected, using defaults")
        except Exception as e:
            logger.warning(f"Could not load calibrated weights: {e} — using defaults")
