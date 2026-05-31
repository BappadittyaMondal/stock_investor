"""
HFOS v5.0 — Technical Engine
Calculates technical_score (0-100) using 15+ indicators.
Uses pandas-ta for all TA calculations.
"""
import logging

import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


class TechnicalEngine:
    """
    Technical Score: 0-100
    Components:
      Trend     (30%): EMA alignment, ADX
      Momentum  (25%): RSI, MACD
      Volume    (20%): OBV trend, Volume ratio
      Structure (15%): ATH proximity, 52w range
      Volatility(10%): ATR-based risk
    """

    def __init__(self):
        pass

    def score(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> float:
        """
        Args:
            df: OHLCV DataFrame with columns open,high,low,close,volume
                Index must be DatetimeIndex or date-like, sorted ascending.
        Returns:
            float 0-100
        """
        if df is None or len(df) < 30:
            logger.warning(f"[{symbol}] Insufficient data for TA ({len(df) if df is not None else 0} rows)")
            return 50.0

        try:
            df = df.copy()
            df.columns = [c.lower() for c in df.columns]

            scores = {
                "trend":      self._trend_score(df),
                "momentum":   self._momentum_score(df),
                "volume":     self._volume_score(df),
                "structure":  self._structure_score(df),
                "volatility": self._volatility_score(df),
            }
            weights = {
                "trend": 0.30, "momentum": 0.25, "volume": 0.20,
                "structure": 0.15, "volatility": 0.10,
            }
            composite = sum(scores[k] * weights[k] for k in scores)
            result = round(max(0.0, min(100.0, composite)), 2)
            logger.debug(f"[{symbol}] TechScore={result:.1f} components={scores}")
            return result
        except Exception as e:
            logger.error(f"[{symbol}] TechnicalEngine error: {e}")
            return 50.0

    # -------------------------------------------------------------------------
    def _trend_score(self, df: pd.DataFrame) -> float:
        score = 0.0
        close = df["close"]

        # EMA 20/50/200 alignment
        ema20  = ta.ema(close, 20)
        ema50  = ta.ema(close, 50)
        ema200 = ta.ema(close, 200) if len(df) >= 200 else None

        last_close = close.iloc[-1]
        e20 = ema20.iloc[-1] if ema20 is not None else None
        e50 = ema50.iloc[-1] if ema50 is not None else None
        e200 = ema200.iloc[-1] if ema200 is not None else None

        # Price above EMA20
        if e20 and last_close > e20:
            score += 25.0
        # EMA20 > EMA50 (bullish alignment)
        if e20 and e50 and e20 > e50:
            score += 25.0
        # Price above EMA200 (long-term trend)
        if e200 and last_close > e200:
            score += 25.0

        # ADX > 25 = trending (not sideways)
        adx_df = ta.adx(df["high"], df["low"], close)
        if adx_df is not None and not adx_df.empty:
            adx_col = [c for c in adx_df.columns if c.startswith("ADX")]
            if adx_col:
                adx_val = adx_df[adx_col[0]].iloc[-1]
                if adx_val > 40:
                    score += 25.0
                elif adx_val > 25:
                    score += 15.0
                elif adx_val > 15:
                    score += 5.0

        return min(100.0, score)

    def _momentum_score(self, df: pd.DataFrame) -> float:
        score = 0.0
        close = df["close"]

        # RSI
        rsi = ta.rsi(close, 14)
        if rsi is not None and not rsi.empty:
            rsi_val = rsi.iloc[-1]
            if 55 <= rsi_val <= 70:   # Bullish momentum, not overbought
                score += 35.0
            elif 45 <= rsi_val < 55:  # Neutral
                score += 20.0
            elif 30 <= rsi_val < 45:  # Oversold recovery zone
                score += 10.0
            elif rsi_val > 70:        # Overbought — caution
                score += 15.0

        # MACD
        macd_df = ta.macd(close)
        if macd_df is not None and not macd_df.empty:
            macd_cols = macd_df.columns.tolist()
            macd_col  = [c for c in macd_cols if "MACD_" in c and "Signal" not in c and "Hist" not in c]
            sig_col   = [c for c in macd_cols if "MACDs" in c]
            hist_col  = [c for c in macd_cols if "MACDh" in c]

            if macd_col and sig_col:
                macd_val = macd_df[macd_col[0]].iloc[-1]
                sig_val  = macd_df[sig_col[0]].iloc[-1]
                if macd_val > sig_val and macd_val > 0:
                    score += 40.0
                elif macd_val > sig_val:
                    score += 25.0
                elif macd_val > 0:
                    score += 10.0

            if hist_col and len(macd_df) >= 2:
                h_now = macd_df[hist_col[0]].iloc[-1]
                h_prev = macd_df[hist_col[0]].iloc[-2]
                if h_now > h_prev and h_now > 0:
                    score += 25.0
                elif h_now > h_prev:
                    score += 10.0

        return min(100.0, score)

    def _volume_score(self, df: pd.DataFrame) -> float:
        score = 0.0
        close = df["close"]
        vol   = df["volume"]

        if len(df) < 20:
            return 50.0

        # Volume vs 20-day average
        avg_vol = vol.rolling(20).mean().iloc[-1]
        last_vol = vol.iloc[-1]
        if avg_vol > 0:
            vol_ratio = last_vol / avg_vol
            if vol_ratio > 2.0:
                score += 40.0
            elif vol_ratio > 1.5:
                score += 30.0
            elif vol_ratio > 1.0:
                score += 20.0
            else:
                score += 5.0

        # OBV trend
        obv = ta.obv(close, vol)
        if obv is not None and len(obv) >= 20:
            obv_ma = obv.rolling(20).mean()
            if obv.iloc[-1] > obv_ma.iloc[-1]:
                score += 30.0
            else:
                score += 10.0

        # Price-volume confirmation (price up + volume up)
        if len(df) >= 2:
            price_up = close.iloc[-1] > close.iloc[-2]
            vol_up   = vol.iloc[-1] > vol.iloc[-2]
            if price_up and vol_up:
                score += 30.0
            elif not price_up and not vol_up:
                score += 10.0
            else:
                score += 15.0

        return min(100.0, score)

    def _structure_score(self, df: pd.DataFrame) -> float:
        score = 0.0
        close = df["close"]
        high  = df["high"]
        low   = df["low"]

        last_close = close.iloc[-1]
        high_52w   = high.rolling(252).max().iloc[-1]
        low_52w    = low.rolling(252).min().iloc[-1]

        if high_52w > low_52w:
            pct_range = (last_close - low_52w) / (high_52w - low_52w)
            # Near 52w high = bullish
            if pct_range > 0.8:
                score += 50.0
            elif pct_range > 0.6:
                score += 35.0
            elif pct_range > 0.4:
                score += 20.0
            else:
                score += 5.0

            # ATH proximity bonus
            if last_close >= high_52w * 0.95:
                score += 20.0

        # Higher highs & higher lows (uptrend structure)
        if len(df) >= 10:
            recent_highs = high.iloc[-10:]
            recent_lows  = low.iloc[-10:]
            hh = (recent_highs.diff().dropna() > 0).sum() > 5
            hl = (recent_lows.diff().dropna() > 0).sum() > 5
            if hh and hl:
                score += 30.0
            elif hh or hl:
                score += 15.0

        return min(100.0, score)

    def _volatility_score(self, df: pd.DataFrame) -> float:
        """Higher score = lower risk volatility (ATR-based)."""
        close = df["close"]
        high  = df["high"]
        low   = df["low"]

        atr = ta.atr(high, low, close, 14)
        if atr is None or atr.empty:
            return 50.0

        atr_val = atr.iloc[-1]
        last_close = close.iloc[-1]
        atr_pct = (atr_val / last_close * 100) if last_close > 0 else 0

        # Lower ATR% = less volatile = higher score
        if atr_pct < 1.5:
            return 85.0
        elif atr_pct < 2.5:
            return 70.0
        elif atr_pct < 4.0:
            return 55.0
        elif atr_pct < 6.0:
            return 35.0
        else:
            return 15.0
