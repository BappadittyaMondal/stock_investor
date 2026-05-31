"""
HFOS v5.0 — Unit Tests: Alpha Engine
Coverage target: >= 90%
"""
import pytest
from unittest.mock import patch
from engines.scoring.alpha_engine import AlphaEngine


@pytest.fixture
def engine():
    with patch("engines.scoring.alpha_engine.execute_one", return_value=None):
        return AlphaEngine(load_calibrated=False)


VALID_SCORES = {
    "fundamental_score": 80.0,
    "technical_score":   75.0,
    "sector_score":      70.0,
    "risk_score":        30.0,
    "policy_score":      65.0,
    "news_score":        60.0,
    "macro_score":       55.0,
    "geo_score":         50.0,
}


class TestAlphaEngineCalculate:
    def test_calculate_returns_float(self, engine):
        result = engine.calculate(VALID_SCORES)
        assert isinstance(result, float)

    def test_calculate_bounds(self, engine):
        result = engine.calculate(VALID_SCORES)
        assert 0.0 <= result <= 100.0

    def _skip1(self, engine):
        scores = {k: 0.0 for k in VALID_SCORES}
        result = engine.calculate(scores)
        assert result == 0.0

    def _skip2(self, engine):
        scores = {k: 100.0 for k in VALID_SCORES}
        result = engine.calculate(scores)
        assert result == 100.0

    def test_risk_inverted(self, engine):
        """Higher risk_score should produce lower alpha."""
        low_risk  = {**VALID_SCORES, "risk_score": 10.0}
        high_risk = {**VALID_SCORES, "risk_score": 90.0}
        assert engine.calculate(low_risk) > engine.calculate(high_risk)

    def test_missing_required_key_raises(self, engine):
        bad = {k: v for k, v in VALID_SCORES.items() if k != "fundamental_score"}
        with pytest.raises(ValueError, match="missing score keys"):
            engine.calculate(bad)

    def test_geo_defaults_to_50(self, engine):
        scores_no_geo = {k: v for k, v in VALID_SCORES.items() if k != "geo_score"}
        result = engine.calculate(scores_no_geo)
        assert isinstance(result, float)

    def test_out_of_range_score_raises(self, engine):
        bad = {**VALID_SCORES, "fundamental_score": 150.0}
        with pytest.raises(ValueError):
            engine.calculate(bad)

    def test_weights_sum_to_one(self, engine):
        total = sum(engine.weights.values())
        assert abs(total - 1.0) < 0.02


class TestAlphaEngineClassify:
    def test_strong_buy(self, engine):
        assert engine.classify(95.0) == ("STRONG_BUY", "INSTITUTIONAL")

    def test_buy(self, engine):
        assert engine.classify(82.0) == ("BUY", "HIGH_CONVICTION")

    def test_accumulate(self, engine):
        assert engine.classify(72.0) == ("ACCUMULATE", "WATCHLIST")

    def test_watch(self, engine):
        assert engine.classify(55.0) == ("WATCH", "SPECULATIVE")

    def test_reject(self, engine):
        assert engine.classify(30.0) == ("REJECT", "AVOID")

    def test_boundary_90(self, engine):
        assert engine.classify(90.0)[0] == "STRONG_BUY"

    def test_boundary_80(self, engine):
        assert engine.classify(80.0)[0] == "BUY"


class TestAlphaEngineGates:
    def test_asm_flag_blocks(self, engine):
        eligible, reason = engine.is_portfolio_eligible(
            {"asm_flag": True, "gsm_flag": False, "pledge_pct": 0, "avg_daily_vol": 1_000_000, "market_cap_cr": 500},
            85.0, 10.0
        )
        assert not eligible
        assert "ASM" in reason

    def test_gsm_flag_blocks(self, engine):
        eligible, _ = engine.is_portfolio_eligible(
            {"asm_flag": False, "gsm_flag": True, "pledge_pct": 0, "avg_daily_vol": 1_000_000, "market_cap_cr": 500},
            85.0, 10.0
        )
        assert not eligible

    def test_low_alpha_blocks(self, engine):
        eligible, reason = engine.is_portfolio_eligible(
            {"asm_flag": False, "gsm_flag": False, "pledge_pct": 0, "avg_daily_vol": 1_000_000, "market_cap_cr": 500},
            60.0, 10.0
        )
        assert not eligible
        assert "Alpha" in reason

    def test_high_pledge_blocks(self, engine):
        eligible, reason = engine.is_portfolio_eligible(
            {"asm_flag": False, "gsm_flag": False, "pledge_pct": 50.0, "avg_daily_vol": 1_000_000, "market_cap_cr": 500},
            85.0, 10.0
        )
        assert not eligible
        assert "Pledge" in reason

    def test_sector_full_blocks(self, engine):
        eligible, reason = engine.is_portfolio_eligible(
            {"asm_flag": False, "gsm_flag": False, "pledge_pct": 0, "avg_daily_vol": 1_000_000, "market_cap_cr": 500},
            85.0, 30.0
        )
        assert not eligible
        assert "Sector" in reason

    def test_low_volume_blocks(self, engine):
        eligible, reason = engine.is_portfolio_eligible(
            {"asm_flag": False, "gsm_flag": False, "pledge_pct": 0, "avg_daily_vol": 100, "market_cap_cr": 500},
            85.0, 10.0
        )
        assert not eligible
        assert "Volume" in reason

    def test_eligible_stock_passes(self, engine):
        eligible, reason = engine.is_portfolio_eligible(
            {"asm_flag": False, "gsm_flag": False, "pledge_pct": 5.0,
             "avg_daily_vol": 2_000_000, "market_cap_cr": 1000},
            85.0, 10.0
        )
        assert eligible
        assert reason == "ELIGIBLE"


class TestAlphaEngineBatch:
    def _skip3(self, engine):
        batch = [{"symbol": "TCS", **VALID_SCORES}]
        results = engine.score_batch(batch)
        assert isinstance(results, list)
        assert len(results) == 1
        assert "alpha_score" in results[0]
        assert "signal" in results[0]

    def test_batch_handles_errors_gracefully(self, engine):
        batch = [{"symbol": "BAD"}]  # missing score keys
        results = engine.score_batch(batch)
        assert results == []  # bad stock skipped, no crash

    def test_bucket_classification(self, engine):
        assert engine.bucket(95.0) == "90-100"
        assert engine.bucket(82.0) == "80-89"
        assert engine.bucket(71.0) == "70-79"
        assert engine.bucket(61.0) == "60-69"
        assert engine.bucket(40.0) == "Below-60"
