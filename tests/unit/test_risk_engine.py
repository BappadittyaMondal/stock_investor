"""
HFOS v5.0 — Unit Tests: Risk Engine
"""
import pytest
from engines.risk.risk_engine import RiskEngine
import pandas as pd
import numpy as np
from datetime import datetime


def _make_df(n: int = 60) -> pd.DataFrame:
    dates = pd.date_range(end=datetime.today(), periods=n, freq="B")
    price = 1000 + np.random.randn(n).cumsum()
    return pd.DataFrame({
        "close": price, "open": price * 0.99,
        "high": price * 1.02, "low": price * 0.98,
        "volume": [500_000] * n
    }, index=dates)


CLEAN_STOCK = {
    "asm_flag": 0, "gsm_flag": 0,
    "pledge_pct": 5.0, "market_cap_cr": 5000.0,
    "avg_daily_vol": 2_000_000,
}

RISKY_STOCK = {
    "asm_flag": 1, "gsm_flag": 1,
    "pledge_pct": 60.0, "market_cap_cr": 100.0,
    "avg_daily_vol": 10_000,
}


@pytest.fixture
def engine():
    return RiskEngine()


class TestRiskEngineScore:
    def test_returns_float(self, engine):
        df = _make_df()
        result = engine.score(CLEAN_STOCK, df)
        assert isinstance(result, float)

    def test_score_in_range(self, engine):
        df = _make_df()
        result = engine.score(CLEAN_STOCK, df)
        assert 0.0 <= result <= 100.0

    def test_risky_stock_scores_higher(self, engine):
        df = _make_df()
        clean = engine.score(CLEAN_STOCK, df)
        risky = engine.score(RISKY_STOCK, df)
        assert risky > clean, f"Risky {risky:.1f} should > Clean {clean:.1f}"

    def test_asm_flag_increases_risk(self, engine):
        df = _make_df()
        no_asm = {**CLEAN_STOCK, "asm_flag": 0}
        with_asm = {**CLEAN_STOCK, "asm_flag": 1}
        assert engine.score(with_asm, df) > engine.score(no_asm, df)

    def test_high_pledge_increases_risk(self, engine):
        df = _make_df()
        low_pledge  = {**CLEAN_STOCK, "pledge_pct": 2.0}
        high_pledge = {**CLEAN_STOCK, "pledge_pct": 55.0}
        assert engine.score(high_pledge, df) > engine.score(low_pledge, df)

    def test_low_market_cap_increases_risk(self, engine):
        df = _make_df()
        large = {**CLEAN_STOCK, "market_cap_cr": 10_000.0}
        small = {**CLEAN_STOCK, "market_cap_cr": 50.0}
        assert engine.score(small, df) > engine.score(large, df)

    def test_none_df_returns_default(self, engine):
        result = engine.score(CLEAN_STOCK, None)
        assert isinstance(result, float)

    def test_empty_stock_returns_default(self, engine):
        df = _make_df()
        result = engine.score({}, df)
        assert isinstance(result, float)


class TestRiskEngineCalibrationEngine:
    """Test CalibrationEngine basic functionality."""
    def test_default_weights_valid(self):
        from engines.calibration.calibration_engine import CalibrationEngine, WEIGHT_KEYS
        cal = CalibrationEngine()
        weights = cal._sample_weights()
        assert len(weights) == len(WEIGHT_KEYS)
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_sharpe_from_returns_zero_std(self):
        from engines.calibration.calibration_engine import CalibrationEngine
        import numpy as np
        cal = CalibrationEngine()
        # All same return → std=0 → sharpe=0
        returns = np.array([1.0, 1.0, 1.0])
        assert cal._sharpe_from_returns(returns) == 0.0

    def test_max_drawdown_no_drawdown(self):
        from engines.calibration.calibration_engine import CalibrationEngine
        import numpy as np
        cal = CalibrationEngine()
        # Monotonically increasing → no drawdown
        returns = np.array([1.0, 2.0, 3.0])
        dd = cal._max_drawdown(returns)
        assert dd >= 0.0

    def test_insufficient_trades_raises(self):
        from engines.calibration.calibration_engine import CalibrationEngine
        from unittest.mock import patch
        cal = CalibrationEngine()
        with patch.object(cal, "_load_trades", return_value=[{"pnl_pct": 1.0}] * 5):
            with pytest.raises(RuntimeError, match="15"):
                cal.run()
