"""
HFOS v5.0 — Data Validation Layer
Pydantic v2 schemas + pandas-level OHLCV validation.
Strict: rejects invalid records, no silent failures.
"""
import re
from datetime import datetime
from typing import Optional, Literal

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Stock Schema
# =============================================================================
class StockCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=200)
    exchange: Literal["NSE", "BSE", "BOTH"] = "NSE"
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap_cr: Optional[float] = Field(None, ge=0)
    isin: Optional[str] = None
    face_value: float = Field(10.0, gt=0)
    is_active: bool = True

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        cleaned = re.sub(r"[^A-Z0-9&-]", "", v.upper().strip())
        if not cleaned:
            raise ValueError("Symbol contains no valid characters")
        return cleaned

    @field_validator("isin")
    @classmethod
    def validate_isin(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().upper()
        if not re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", v):
            raise ValueError(f"Invalid ISIN format: {v}")
        return v


# =============================================================================
# Fundamental Schema
# =============================================================================
class FundamentalCreate(BaseModel):
    stock_id: int
    report_date: str
    period_type: Literal["QUARTERLY", "ANNUAL", "TTM"] = "QUARTERLY"
    revenue_cr: Optional[float] = Field(None, ge=0)
    ebitda_cr: Optional[float] = None
    pat_cr: Optional[float] = None
    eps: Optional[float] = None
    pe_ratio: Optional[float] = Field(None, ge=0, le=10000)
    pb_ratio: Optional[float] = Field(None, ge=0, le=1000)
    roe_pct: Optional[float] = Field(None, ge=-500, le=500)
    roce_pct: Optional[float] = Field(None, ge=-500, le=500)
    debt_equity: Optional[float] = Field(None, ge=0)
    current_ratio: Optional[float] = Field(None, ge=0)
    promoter_holding: Optional[float] = Field(None, ge=0, le=100)
    fii_holding: Optional[float] = Field(None, ge=0, le=100)
    dii_holding: Optional[float] = Field(None, ge=0, le=100)
    pledged_pct: float = Field(0.0, ge=0, le=100)
    dividend_yield: float = Field(0.0, ge=0)
    revenue_growth_yoy: Optional[float] = None
    pat_growth_yoy: Optional[float] = None
    operating_cf: Optional[float] = None
    fcf_cr: Optional[float] = None
    source: str = "screener"

    @field_validator("report_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"report_date must be YYYY-MM-DD, got: {v}")
        return v


# =============================================================================
# Score Schema
# =============================================================================
class ScoreCreate(BaseModel):
    stock_id: int
    fundamental_score: float = Field(..., ge=0, le=100)
    technical_score: float = Field(..., ge=0, le=100)
    sector_score: float = Field(..., ge=0, le=100)
    risk_score: float = Field(..., ge=0, le=100)
    policy_score: float = Field(..., ge=0, le=100)
    news_score: float = Field(..., ge=0, le=100)
    macro_score: float = Field(..., ge=0, le=100)
    geo_score: float = Field(50.0, ge=0, le=100)
    alpha_score: float = Field(..., ge=0, le=100)
    signal: Literal["STRONG_BUY", "BUY", "ACCUMULATE", "WATCH", "REJECT"]
    confidence: Literal["INSTITUTIONAL", "HIGH_CONVICTION", "WATCHLIST", "SPECULATIVE", "AVOID"]
    weight_version: str = "v5.0"


# =============================================================================
# Portfolio Schema
# =============================================================================
class PortfolioCreate(BaseModel):
    stock_id: int
    quantity: int = Field(..., gt=0)
    avg_cost: float = Field(..., gt=0)
    entry_date: str
    stop_loss: Optional[float] = Field(None, gt=0)
    target_price: Optional[float] = Field(None, gt=0)
    position_size: Optional[float] = Field(None, ge=0, le=100)
    tier: Optional[Literal["TIER1", "TIER2", "TIER3", "TIER4"]] = None
    strategy: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_sl_target(self) -> "PortfolioCreate":
        if self.stop_loss and self.target_price:
            if self.stop_loss >= self.avg_cost:
                raise ValueError("stop_loss must be below avg_cost")
            if self.target_price <= self.avg_cost:
                raise ValueError("target_price must be above avg_cost")
        return self


# =============================================================================
# Alert Schema
# =============================================================================
class AlertCreate(BaseModel):
    alert_type: str = Field(..., min_length=1)
    stock_id: Optional[int] = None
    message: str = Field(..., min_length=1, max_length=4096)
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    delivery_method: Literal["TELEGRAM", "EMAIL", "BOTH", "LOG"] = "TELEGRAM"


# =============================================================================
# OHLCV DataFrame Validator
# =============================================================================
class DataValidator:
    REQUIRED_COLS = {"open", "high", "low", "close", "volume"}
    PRICE_MIN = 0.01
    PRICE_MAX = 1_000_000.0

    @classmethod
    def validate_ohlcv(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean OHLCV DataFrame. Raises ValueError on fatal issues."""
        if df is None or df.empty:
            raise ValueError("OHLCV DataFrame is empty or None")

        df.columns = [c.lower() for c in df.columns]
        missing = cls.REQUIRED_COLS - set(df.columns)
        if missing:
            raise ValueError(f"OHLCV missing required columns: {missing}")

        # Price sanity
        for col in ("open", "high", "low", "close"):
            invalid_mask = (df[col] < cls.PRICE_MIN) | (df[col] > cls.PRICE_MAX)
            if invalid_mask.any():
                df = df[~invalid_mask]

        # OHLC consistency
        bad_hl = df["high"] < df["low"]
        bad_oc = (df["close"] > df["high"] * 1.2) | (df["close"] < df["low"] * 0.8)
        df = df[~(bad_hl | bad_oc)]

        # No negative volumes
        df = df[df["volume"] >= 0]

        # Drop NaN rows
        df = df.dropna(subset=["open", "high", "low", "close"])

        if df.empty:
            raise ValueError("OHLCV DataFrame empty after validation")

        return df

    @classmethod
    def validate_score(cls, score: float, name: str = "score") -> float:
        """Validate a 0-100 score. Raises ValueError if out of range."""
        if not isinstance(score, (int, float)) or np.isnan(score):
            raise ValueError(f"{name} must be a number, got: {score}")
        if not (0.0 <= score <= 100.0):
            raise ValueError(f"{name}={score:.2f} out of range [0,100]")
        return round(float(score), 4)

    @classmethod
    def validate_percentage(cls, value: float, name: str = "value") -> float:
        if not (0.0 <= value <= 100.0):
            raise ValueError(f"{name}={value:.2f} out of range [0,100]")
        return round(float(value), 4)
