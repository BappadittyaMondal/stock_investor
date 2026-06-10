"""
HFOS v5.0 - Unit Tests: Universal Screener
"""
from unittest.mock import patch

from engines.screener.universal_screener import UniversalScreener


def test_nested_filters_and_operators():
    with patch("engines.screener.universal_screener.DataFetcher") as mock_fetcher:
        mock_fetcher.return_value.fetch_ohlcv.return_value = None
        screener = UniversalScreener()
        payload = {
            "symbol": "ABC",
            "name": "ABC Ltd",
            "roe_pct": 22,
            "roce_pct": 24,
            "debt_equity": 0.4,
            "promoter_holding": 55,
            "revenue_growth_yoy": 18,
            "pat_growth_yoy": 19,
            "cash_flow_quality_pct": 90,
        }
        definition = {
            "all": [
                {"field": "roe_pct", "operator": ">=", "value": 20},
                {
                    "any": [
                        {"field": "debt_equity", "operator": "<=", "value": 0.5},
                        {"field": "promoter_holding", "operator": ">=", "value": 60},
                    ]
                },
            ]
        }
        result = screener.evaluate(definition, payload)
        assert result.passed is True
        assert "roe_pct" in result.matched
        assert result.unsupported == []


def test_in_and_between_operators():
    with patch("engines.screener.universal_screener.DataFetcher") as mock_fetcher:
        mock_fetcher.return_value.fetch_ohlcv.return_value = None
        screener = UniversalScreener()
        payload = {"symbol": "ABC", "name": "ABC Ltd", "sector": "IT", "score": 75}
        assert screener._compare("IT", "IN", ["IT", "FMCG"]) is True
        assert screener._compare(12, "BETWEEN", [10, 15]) is True


def test_arithmetic_expression_node():
    with patch("engines.screener.universal_screener.DataFetcher") as mock_fetcher:
        mock_fetcher.return_value.fetch_ohlcv.return_value = None
        screener = UniversalScreener()
        payload = {
            "symbol": "ABC",
            "name": "ABC Ltd",
            "revenue_cr": 100.0,
            "pat_cr": 12.0,
        }
        result = screener.evaluate(
            {
                "expr": {
                    "name": "PAT margin proxy",
                    "left": {"field": "pat_cr"},
                    "operator": "/",
                    "right": {"field": "revenue_cr"},
                    "compare": ">=",
                    "value": 0.1,
                }
            },
            payload,
        )
        assert result.passed is True
