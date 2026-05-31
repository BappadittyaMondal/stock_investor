"""
HFOS v5.0 — Unit Tests: Portfolio Service
"""
import pytest
from services.portfolio_service import PortfolioService


@pytest.fixture
def ps():
    return PortfolioService()


class TestPositionSizing:
    def test_basic_sizing(self, ps):
        result = ps.calculate_position_size(
            alpha_score=80.0,
            current_price=1000.0,
            stop_loss=920.0,
        )
        assert "shares" in result
        assert result["shares"] > 0
        assert result["position_pct"] <= 10.0
        assert result["stop_loss"] == 920.0
        assert result["target"] > 1000.0

    def test_sl_above_price_raises(self, ps):
        with pytest.raises(ValueError):
            ps.calculate_position_size(
                alpha_score=80.0, current_price=1000.0, stop_loss=1100.0
            )

    def test_position_capped_at_max(self, ps):
        result = ps.calculate_position_size(
            alpha_score=80.0, current_price=10.0, stop_loss=9.0
        )
        assert result["position_pct"] <= 10.0

    def test_higher_alpha_larger_position(self, ps):
        low  = ps.calculate_position_size(75.0, 1000.0, 920.0)
        high = ps.calculate_position_size(98.0, 1000.0, 920.0)
        assert high["shares"] >= low["shares"]

    def test_suggest_stop_loss_atr(self, ps):
        sl = ps.suggest_stop_loss(1000.0, atr=15.0)
        assert sl == 970.0  # 1000 - 2*15

    def test_suggest_stop_loss_default(self, ps):
        sl = ps.suggest_stop_loss(1000.0, atr=None)
        assert 800.0 <= sl < 1000.0


class TestXIRR:
    def test_xirr_simple_gain(self, ps):
        """XIRR on simple buy-then-sell with gain."""
        from datetime import date
        cashflows = [-10000.0, 12000.0]
        dates     = [date(2023, 1, 1), date(2024, 1, 1)]
        xirr = ps._xirr(cashflows, dates)
        assert xirr is not None
        assert 0.18 < xirr < 0.22  # ~20% annual return

    def test_xirr_empty(self, ps):
        result = ps._xirr([], [])
        assert result is None

    def test_xirr_insufficient_data(self, ps):
        from datetime import date
        result = ps._xirr([-1000.0], [date(2023, 1, 1)])
        assert result is None


class TestTaxLogic:
    def test_stcg_under_1_year(self, ps):
        result = ps.estimate_tax("2024-01-01", "2024-06-01", 100.0, 130.0, 100)
        assert result["tax_type"] == "STCG"
        assert result["tax_rate_pct"] == 20.0
        assert result["holding_days"] < 365

    def test_ltcg_over_1_year(self, ps):
        result = ps.estimate_tax("2022-01-01", "2024-01-02", 100.0, 200.0, 100)
        assert result["tax_type"] == "LTCG"
        assert result["tax_rate_pct"] == 12.5

    def test_no_tax_on_loss(self, ps):
        result = ps.estimate_tax("2024-01-01", "2024-12-01", 200.0, 150.0, 100)
        assert result["estimated_tax"] == 0.0

    def test_ltcg_exemption_applied(self, ps):
        # Gain < 1.25L → no LTCG tax
        result = ps.estimate_tax("2022-01-01", "2024-01-02", 100.0, 200.0, 100)
        # gain = 100 * 100 = 10000 → well below exemption
        assert result["estimated_tax"] == 0.0
