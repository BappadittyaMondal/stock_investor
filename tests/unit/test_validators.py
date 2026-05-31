"""
HFOS v5.0 — Unit Tests: Validators
"""
import pytest
import pandas as pd
import numpy as np
from schemas.validators import DataValidator, StockCreate, PortfolioCreate


class TestDataValidatorOHLCV:
    def _make_df(self, n=50, bad=None):
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        data  = {
            "open":   np.random.uniform(100, 200, n),
            "high":   np.random.uniform(200, 250, n),
            "low":    np.random.uniform(80,  100, n),
            "close":  np.random.uniform(100, 200, n),
            "volume": np.random.randint(100000, 1000000, n),
        }
        df = pd.DataFrame(data, index=dates)
        if bad:
            df.loc[df.index[0], bad] = -99
        return df

    def test_valid_df_passes(self):
        df = self._make_df()
        result = DataValidator.validate_ohlcv(df)
        assert not result.empty

    def test_empty_df_raises(self):
        with pytest.raises(ValueError, match="empty"):
            DataValidator.validate_ohlcv(pd.DataFrame())

    def test_none_raises(self):
        with pytest.raises((ValueError, AttributeError)):
            DataValidator.validate_ohlcv(None)

    def test_missing_column_raises(self):
        df = self._make_df().drop(columns=["volume"])
        with pytest.raises(ValueError, match="missing"):
            DataValidator.validate_ohlcv(df)

    def test_negative_price_removed(self):
        df = self._make_df()
        df.loc[df.index[0], "close"] = -5.0
        result = DataValidator.validate_ohlcv(df)
        assert len(result) < len(df)

    def test_case_insensitive_columns(self):
        df = self._make_df()
        df.columns = [c.upper() for c in df.columns]
        result = DataValidator.validate_ohlcv(df)
        assert not result.empty

    def test_validate_score_valid(self):
        assert DataValidator.validate_score(75.0) == 75.0

    def test_validate_score_out_of_range(self):
        with pytest.raises(ValueError):
            DataValidator.validate_score(105.0)

    def test_validate_score_nan(self):
        with pytest.raises(ValueError):
            DataValidator.validate_score(float("nan"))


class TestStockCreate:
    def test_valid_stock(self):
        s = StockCreate(symbol="TCS", name="Tata Consultancy", exchange="NSE")
        assert s.symbol == "TCS"

    def test_symbol_normalized_to_upper(self):
        s = StockCreate(symbol="tcs", name="TCS")
        assert s.symbol == "TCS"

    def test_invalid_exchange(self):
        with pytest.raises(Exception):
            StockCreate(symbol="TCS", name="TCS", exchange="NYSE")

    def test_valid_isin(self):
        s = StockCreate(symbol="TCS", name="TCS", isin="INE467B01029")
        assert s.isin == "INE467B01029"

    def test_invalid_isin(self):
        with pytest.raises(Exception):
            StockCreate(symbol="TCS", name="TCS", isin="INVALID")

    def test_empty_symbol_raises(self):
        with pytest.raises(Exception):
            StockCreate(symbol="", name="TCS")


class TestPortfolioCreate:
    def test_valid_position(self):
        p = PortfolioCreate(
            stock_id=1, quantity=100, avg_cost=1500.0,
            entry_date="2024-01-15", stop_loss=1380.0, target_price=1800.0
        )
        assert p.quantity == 100

    def test_zero_quantity_raises(self):
        with pytest.raises(Exception):
            PortfolioCreate(stock_id=1, quantity=0, avg_cost=100.0, entry_date="2024-01-01")

    def test_negative_cost_raises(self):
        with pytest.raises(Exception):
            PortfolioCreate(stock_id=1, quantity=10, avg_cost=-100.0, entry_date="2024-01-01")

    def test_sl_above_avg_cost_raises(self):
        with pytest.raises(ValueError, match="stop_loss"):
            PortfolioCreate(
                stock_id=1, quantity=10, avg_cost=100.0,
                entry_date="2024-01-01", stop_loss=120.0, target_price=150.0
            )

    def test_target_below_avg_cost_raises(self):
        with pytest.raises(ValueError, match="target_price"):
            PortfolioCreate(
                stock_id=1, quantity=10, avg_cost=100.0,
                entry_date="2024-01-01", stop_loss=90.0, target_price=90.0
            )
