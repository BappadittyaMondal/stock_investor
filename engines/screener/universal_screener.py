"""
HFOS v5.0 - Universal Screener Engine

Dynamic filter evaluation over the existing SQLite-backed market data.
Supports nested AND/OR groups and the operator set needed for PDF screeners.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
import operator
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

from database.db_manager import execute_query
from services.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


OPS = {"=", "!=", ">", "<", ">=", "<=", "BETWEEN", "IN", "NOT IN"}
ARITHMETIC_OPS = {"+", "-", "*", "/"}


@dataclass(frozen=True)
class FilterResult:
    symbol: str
    name: str
    passed: bool
    score: float
    matched: list[str]
    unsupported: list[str]
    payload: dict[str, Any]


class UniversalScreener:
    """
    Evaluate arbitrarily nested filter trees against the HFOS universe.
    """

    def __init__(self) -> None:
        self.fetcher = DataFetcher()
        self._templates = self._load_templates()

    def list_templates(self) -> dict[str, Any]:
        return self._templates

    def run(self, definition: dict[str, Any], limit: Optional[int] = None) -> list[dict[str, Any]]:
        rows = execute_query(
            """
            SELECT s.id, s.symbol, s.name, s.sector, s.market_cap_cr,
                   s.pledge_pct, s.avg_daily_vol, s.asm_flag, s.gsm_flag
            FROM stocks s
            WHERE s.is_active=1
            ORDER BY COALESCE(s.market_cap_cr, 0) DESC, s.symbol ASC
            """
        )
        results: list[dict[str, Any]] = []
        for row in rows[:limit] if limit else rows:
            payload = self._build_payload(dict(row))
            result = self.evaluate(definition, payload)
            if result.passed:
                results.append(
                    {
                        "symbol": row["symbol"],
                        "name": row["name"],
                        "score": round(result.score, 2),
                        "matched": result.matched,
                        "unsupported": result.unsupported,
                        "payload": result.payload,
                    }
                )
        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    def evaluate(self, definition: dict[str, Any], payload: dict[str, Any]) -> FilterResult:
        matched: list[str] = []
        unsupported: list[str] = []
        passed, score = self._eval_node(definition, payload, matched, unsupported)
        return FilterResult(
            symbol=payload.get("symbol", ""),
            name=payload.get("name", ""),
            passed=passed,
            score=score,
            matched=matched,
            unsupported=unsupported,
            payload=payload,
        )

    def _eval_node(
        self,
        node: dict[str, Any],
        payload: dict[str, Any],
        matched: list[str],
        unsupported: list[str],
    ) -> tuple[bool, float]:
        if "all" in node:
            scores = []
            for child in node["all"]:
                passed, score = self._eval_node(child, payload, matched, unsupported)
                scores.append(score)
                if not passed:
                    return False, sum(scores) / len(scores) if scores else 0.0
            return True, sum(scores) / len(scores) if scores else 0.0
        if "any" in node:
            scores = []
            for child in node["any"]:
                passed, score = self._eval_node(child, payload, matched, unsupported)
                scores.append(score)
                if passed:
                    return True, max(scores) if scores else 0.0
            return False, max(scores) if scores else 0.0
        if "expr" in node:
            return self._eval_expression(node["expr"], payload, matched, unsupported)
        return self._eval_condition(node, payload, matched, unsupported)

    def _eval_expression(
        self,
        expr: dict[str, Any],
        payload: dict[str, Any],
        matched: list[str],
        unsupported: list[str],
    ) -> tuple[bool, float]:
        left = self._resolve_operand(expr.get("left"), payload)
        right = self._resolve_operand(expr.get("right"), payload)
        op = str(expr.get("operator", "")).strip()
        target = expr.get("value")
        if op not in ARITHMETIC_OPS:
            unsupported.append("expression")
            return False, 0.0
        if left is None or right is None:
            unsupported.append("expression")
            return False, 0.0
        actual = self._apply_arithmetic(left, right, op)
        if actual is None:
            unsupported.append("expression")
            return False, 0.0
        passed = self._compare(actual, str(expr.get("compare", "=")).upper(), target)
        if passed:
            matched.append(expr.get("name", "expression"))
        return passed, 1.0 if passed else 0.0

    def _eval_condition(
        self,
        condition: dict[str, Any],
        payload: dict[str, Any],
        matched: list[str],
        unsupported: list[str],
    ) -> tuple[bool, float]:
        field = condition.get("field")
        operator = str(condition.get("operator", "")).upper()
        value = condition.get("value")
        metric = self._resolve_metric(field, payload)
        if operator not in OPS:
            unsupported.append(field or "unknown")
            return False, 0.0
        if metric is None:
            unsupported.append(field or "unknown")
            return False, 0.0
        result = self._compare(metric, operator, value)
        if result:
            matched.append(field)
        return result, 1.0 if result else 0.0

    def _compare(self, actual: Any, operator: str, expected: Any) -> bool:
        if operator == "=":
            return actual == expected
        if operator == "!=":
            return actual != expected
        if operator == ">":
            return actual > expected
        if operator == "<":
            return actual < expected
        if operator == ">=":
            return actual >= expected
        if operator == "<=":
            return actual <= expected
        if operator == "BETWEEN":
            low, high = expected
            return low <= actual <= high
        if operator == "IN":
            return actual in expected
        if operator == "NOT IN":
            return actual not in expected
        return False

    def _apply_arithmetic(self, left: float, right: float, op: str) -> Optional[float]:
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                return None
            return left / right
        return None

    def _resolve_operand(self, operand: Any, payload: dict[str, Any]) -> Any:
        if isinstance(operand, (int, float)):
            return float(operand)
        if isinstance(operand, str):
            return self._resolve_metric(operand, payload)
        if isinstance(operand, dict):
            if "field" in operand:
                return self._resolve_metric(operand["field"], payload)
            if "value" in operand:
                return operand["value"]
        return None

    def _resolve_metric(self, field: str | None, payload: dict[str, Any]) -> Any:
        if not field:
            return None
        key = field.strip().lower().replace(" ", "_")
        aliases = {
            "sales": "revenue_cr",
            "sales_latest_quarter": "quarterly_sales_latest",
            "profit_after_tax": "pat_cr",
            "profit_after_tax_latest_quarter": "quarterly_pat_latest",
            "profit_after_tax_last_year": "pat_last_year",
            "sales_last_year": "sales_last_year",
            "operating_profit_last_year": "operating_profit_last_year",
            "operating_profit_latest_quarter": "quarterly_op_profit_latest",
            "ebitda_last_year": "ebitda_last_year",
            "ebitda_latest_quarter": "quarterly_ebitda_latest",
            "current_price": "last_close",
            "price_to_earning": "pe_ratio",
            "price_to_earnings": "pe_ratio",
            "price_to_book_value": "pb_ratio",
            "return_on_equity": "roe_pct",
            "return_on_capital_employed": "roce_pct",
            "return_on_assets": "roa_pct",
            "debt_to_equity": "debt_equity",
            "debt": "total_debt_cr",
            "current_ratio": "current_ratio",
            "interest_coverage_ratio": "interest_coverage_ratio",
            "dividend_yield": "dividend_yield",
            "earnings_yield": "earnings_yield",
            "industry_pe": "industry_pe",
            "price_to_sales": "price_to_sales",
            "price_to_free_cash_flow": "price_to_free_cash_flow",
            "ev_ebitda": "ev_ebitda",
            "enterprise_value": "enterprise_value",
            "sales_growth": "revenue_growth_yoy",
            "profit_growth": "pat_growth_yoy",
            "yoy_quarterly_sales_growth": "quarterly_sales_growth_yoy",
            "yoy_quarterly_profit_growth": "quarterly_pat_growth_yoy",
            "promoter_holding": "promoter_holding",
            "change_in_promoter_holding": "promoter_change_pct",
            "change_in_fii_holding": "fii_change_pct",
            "change_in_dii_holding": "dii_change_pct",
            "fii_holding": "fii_holding",
            "dii_holding": "dii_holding",
            "public_holding": "public_holding",
            "unpledged_promoter_holding": "unpledged_promoter_holding",
            "pledged_percentage": "pledged_pct",
            "volume": "volume",
            "high_price": "high_52w",
            "low_price": "low_52w",
            "return_over_1_day": "return_1d",
            "return_over_1_week": "return_1w",
            "return_over_1_month": "return_1m",
            "return_over_3_months": "return_3m",
            "return_over_6_months": "return_6m",
            "return_over_1_year": "return_1y",
            "return_over_3_years": "return_3y",
            "return_over_5_years": "return_5y",
            "return_over_7_years": "return_7y",
            "return_over_10_years": "return_10y",
            "dma_50": "dma_50",
            "dma_200": "dma_200",
            "rsi": "rsi",
            "macd": "macd",
            "macd_signal": "macd_signal",
            "is_sme": "is_sme",
            "is_not_sme": "is_sme",
            "52_week_index": "fifty_two_week_index",
            "52w_index": "fifty_two_week_index",
            "52_week_high_index": "fifty_two_week_index",
            "fii_change": "fii_change_pct",
            "dii_change": "dii_change_pct",
            "promoter_change": "promoter_change_pct",
            "volume_expansion": "volume_expansion_ratio",
            "cash_flow_quality": "cash_flow_quality_pct",
            "cfo_vs_pat": "cfo_vs_pat_pct",
            "working_capital_days": "working_capital_days",
            "asset_turnover_ratio": "asset_turnover_ratio",
            "debtors_days": "debtor_days",
            "peg_ratio": "peg_ratio",
            "inventory_turnover_ratio": "inventory_turnover_ratio",
            "cash_conversion_cycle": "cash_conversion_cycle",
            "days_payable_outstanding": "days_payable_outstanding",
            "days_receivable_outstanding": "days_receivable_outstanding",
            "days_inventory_outstanding": "days_inventory_outstanding",
            "piotroski_score": "piotroski_score",
            "g_factor": "g_factor",
            "financial_leverage": "financial_leverage",
            "return_on_invested_capital": "roic_pct",
            "credit_rating": "credit_rating",
            "exports_percentage": "exports_percentage",
            "expected_quarterly_sales_growth": "expected_quarterly_sales_growth",
            "expected_quarterly_sales": "expected_quarterly_sales",
            "expected_quarterly_operating_profit": "expected_quarterly_operating_profit",
            "expected_quarterly_net_profit": "expected_quarterly_net_profit",
            "expected_quarterly_eps": "expected_quarterly_eps",
            "ttm_result_date": "report_date",
            "last_annual_result_date": "last_annual_result_date",
            "last_result_date": "last_result_date",
        }
        key = aliases.get(key, key)
        if key == "is_sme":
            value = payload.get("is_sme")
            if value is None:
                return None
            return not value if field.strip().lower() == "is_not_sme" else value
        return payload.get(key)

    def _build_payload(self, stock: dict[str, Any]) -> dict[str, Any]:
        payload = dict(stock)
        payload.update(self._latest_fundamentals(stock["id"]))
        payload.update(self._latest_ohlcv_metrics(stock["symbol"]))
        payload.update(self._latest_flow_metrics(stock["id"]))
        payload.update(self._latest_historical_metrics(stock["id"]))
        payload.update(self._latest_technical_metrics(stock["symbol"]))
        payload["peg_ratio"] = self._peg_ratio(payload)
        payload["cash_flow_quality_pct"] = self._cash_flow_quality(payload)
        payload["cfo_vs_pat_pct"] = self._cfo_vs_pat(payload)
        payload["asset_turnover_ratio"] = self._asset_turnover(payload)
        payload["fifty_two_week_index"] = self._fifty_two_week_index(payload)
        payload["volume_expansion_ratio"] = self._volume_expansion(payload)
        payload["working_capital_days"] = self._working_capital_days(payload)
        payload["debtor_days"] = self._debtor_days(payload)
        return payload

    def _latest_fundamentals(self, stock_id: int) -> dict[str, Any]:
        row = execute_query(
            """
            SELECT * FROM fundamentals
            WHERE stock_id=?
            ORDER BY report_date DESC
            LIMIT 1
            """,
            (stock_id,),
        )
        return dict(row[0]) if row else {}

    def _latest_ohlcv_metrics(self, symbol: str) -> dict[str, Any]:
        df = self.fetcher.fetch_ohlcv(symbol, days=420)
        if df is None or df.empty:
            return {}
        latest = df.iloc[-1]
        high_52w = float(df["high"].tail(252).max())
        low_52w = float(df["low"].tail(252).min())
        close = float(latest["close"])
        avg_vol_20 = float(df["volume"].tail(20).mean()) if "volume" in df else None
        avg_vol_50 = float(df["volume"].tail(50).mean()) if "volume" in df else None
        return {
            "last_close": close,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "volume": float(latest.get("volume", 0) or 0),
            "avg_volume_20": avg_vol_20,
            "avg_volume_50": avg_vol_50,
            "fifty_two_week_index": round((close / high_52w) * 100, 2) if high_52w else None,
            "volume_expansion_ratio": round((float(latest.get("volume", 0) or 0) / avg_vol_20), 2) if avg_vol_20 else None,
        }

    def _latest_flow_metrics(self, stock_id: int) -> dict[str, Any]:
        rows = execute_query(
            """
            SELECT activity_date, fii_net_cr, dii_net_cr
            FROM fii_dii_activity
            ORDER BY activity_date DESC
            LIMIT 20
            """
        )
        if not rows:
            return {}
        df = pd.DataFrame([dict(r) for r in rows])
        return {
            "fii_change_pct": self._change_pct(df["fii_net_cr"].tolist()),
            "dii_change_pct": self._change_pct(df["dii_net_cr"].tolist()),
            "promoter_change_pct": self._promoter_change(stock_id),
        }

    def _latest_historical_metrics(self, stock_id: int) -> dict[str, Any]:
        row = execute_query(
            """
            SELECT
              MAX(CASE WHEN period_type='TTM' THEN revenue_cr END) AS sales_last_year,
              MAX(CASE WHEN period_type='TTM' THEN ebitda_cr END) AS ebitda_last_year,
              MAX(CASE WHEN period_type='TTM' THEN pat_cr END) AS pat_last_year,
              MAX(CASE WHEN period_type='TTM' THEN revenue_cr END) AS annual_sales,
              MAX(CASE WHEN period_type='TTM' THEN pat_cr END) AS annual_pat
            FROM fundamentals
            WHERE stock_id=?
            """,
            (stock_id,),
        )
        data = dict(row[0]) if row else {}
        return {
            **data,
            "quarterly_sales_latest": data.get("sales_last_year"),
            "quarterly_pat_latest": data.get("pat_last_year"),
            "quarterly_op_profit_latest": data.get("ebitda_last_year"),
            "quarterly_ebitda_latest": data.get("ebitda_last_year"),
            "quarterly_sales_growth_yoy": None,
            "quarterly_pat_growth_yoy": None,
        }

    def _latest_technical_metrics(self, symbol: str) -> dict[str, Any]:
        df = self.fetcher.fetch_ohlcv(symbol, days=1200)
        if df is None or df.empty:
            return {}
        close = df["close"]
        return {
            "dma_50": float(close.tail(50).mean()),
            "dma_200": float(close.tail(200).mean()) if len(close) >= 200 else float(close.mean()),
            "return_1d": round(((close.iloc[-1] / close.iloc[-2]) - 1) * 100, 2) if len(close) >= 2 else None,
            "return_1w": round(((close.iloc[-1] / close.iloc[-6]) - 1) * 100, 2) if len(close) >= 6 else None,
            "return_1m": round(((close.iloc[-1] / close.iloc[-21]) - 1) * 100, 2) if len(close) >= 21 else None,
            "return_3m": round(((close.iloc[-1] / close.iloc[-63]) - 1) * 100, 2) if len(close) >= 63 else None,
            "return_6m": round(((close.iloc[-1] / close.iloc[-126]) - 1) * 100, 2) if len(close) >= 126 else None,
            "return_1y": round(((close.iloc[-1] / close.iloc[-252]) - 1) * 100, 2) if len(close) >= 252 else None,
            "return_3y": round(((close.iloc[-1] / close.iloc[-756]) - 1) * 100, 2) if len(close) >= 756 else None,
            "return_5y": None,
            "return_7y": None,
            "return_10y": None,
        }

    def _change_pct(self, values: list[Any]) -> Optional[float]:
        nums = [float(v) for v in values if v is not None]
        if len(nums) < 2 or nums[-2] == 0:
            return None
        return round(((nums[0] - nums[-1]) / abs(nums[-1])) * 100, 2)

    def _promoter_change(self, stock_id: int) -> Optional[float]:
        rows = execute_query(
            """
            SELECT promoter_holding
            FROM fundamentals
            WHERE stock_id=? AND promoter_holding IS NOT NULL
            ORDER BY report_date DESC
            LIMIT 2
            """,
            (stock_id,),
        )
        vals = [r["promoter_holding"] for r in rows if r["promoter_holding"] is not None]
        if len(vals) < 2 or vals[-1] == 0:
            return None
        return round(vals[0] - vals[1], 2)

    def _peg_ratio(self, payload: dict[str, Any]) -> Optional[float]:
        pe = payload.get("pe_ratio")
        growth = payload.get("pat_growth_yoy") or payload.get("revenue_growth_yoy")
        if pe is None or not growth:
            return None
        return round(pe / max(growth, 1e-6), 2)

    def _cash_flow_quality(self, payload: dict[str, Any]) -> Optional[float]:
        ocf = payload.get("operating_cf")
        pat = payload.get("pat_cr")
        if ocf is None or pat in (None, 0):
            return None
        return round((ocf / abs(pat)) * 100, 2)

    def _cfo_vs_pat(self, payload: dict[str, Any]) -> Optional[float]:
        ocf = payload.get("operating_cf")
        pat = payload.get("pat_cr")
        if ocf is None or pat in (None, 0):
            return None
        return round((ocf / abs(pat)) * 100, 2)

    def _asset_turnover(self, payload: dict[str, Any]) -> Optional[float]:
        revenue = payload.get("revenue_cr")
        total_assets = payload.get("total_assets_cr")
        if revenue is None or not total_assets:
            return None
        return round(revenue / total_assets, 2)

    def _working_capital_days(self, payload: dict[str, Any]) -> Optional[float]:
        inventory_days = payload.get("inventory_days")
        receivable_days = payload.get("debtor_days")
        payable_days = payload.get("creditor_days")
        if None in (inventory_days, receivable_days, payable_days):
            return None
        return round(inventory_days + receivable_days - payable_days, 2)

    def _debtor_days(self, payload: dict[str, Any]) -> Optional[float]:
        revenue = payload.get("revenue_cr")
        receivables = payload.get("trade_receivables_cr")
        if revenue is None or not receivables:
            return None
        return round((receivables / revenue) * 365, 2)

    def _fifty_two_week_index(self, payload: dict[str, Any]) -> Optional[float]:
        close = payload.get("last_close")
        high = payload.get("high_52w")
        if close is None or not high:
            return None
        return round((close / high) * 100, 2)

    def _volume_expansion(self, payload: dict[str, Any]) -> Optional[float]:
        return payload.get("volume_expansion_ratio")

    def _load_templates(self) -> dict[str, Any]:
        path = Path(__file__).resolve().parents[2] / "database" / "screener_templates.json"
        if not path.exists():
            return {"categories": []}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Failed to load screener templates: {exc}")
            return {"categories": []}
