"""
HFOS v5.0 — Data Fetcher Service
Multi-source OHLCV with retry, circuit breaker, and DB cache fallback.
Sources: yfinance → nsepython → DB cache (Level 1/2/3 fallback chain)
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from database.db_manager import execute_one, execute_write, execute_many
from schemas.validators import DataValidator
from config.settings import (
    MAX_RETRY_ATTEMPTS, RETRY_BACKOFF_FACTOR, REQUEST_TIMEOUT_SECS
)

logger = logging.getLogger(__name__)


def _retry_with_backoff(fn, symbol: str, attempts: int, backoff: float):
    """Generic retry with exponential backoff."""
    delay = 1.0
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            result = fn(symbol)
            if result is not None and not result.empty:
                return result
        except Exception as e:
            last_exc = e
            logger.debug(f"[{symbol}] attempt {attempt} failed: {e}")
        if attempt < attempts:
            time.sleep(delay)
            delay *= backoff
    return None


class DataFetcher:
    """
    Multi-source OHLCV fetcher with 3-level fallback:
      L1: yfinance  (free, reliable for NSE)
      L2: nsepython (NSE official data)
      L3: SQLite DB cache (stale but valid)
    Failure escalation: WARN → FALLBACK → SIGNAL_FREEZE
    """

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path  # retained for compatibility; path comes from settings

    # -------------------------------------------------------------------------
    # PUBLIC
    # -------------------------------------------------------------------------
    def fetch_ohlcv(self, symbol: str, days: int = 365) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV for `symbol`. Returns validated DataFrame or None.
        Writes to DB cache on success.
        """
        # L1 — yfinance
        df = _retry_with_backoff(
            lambda s: self._try_yfinance(s, days),
            symbol, MAX_RETRY_ATTEMPTS, RETRY_BACKOFF_FACTOR
        )
        if df is not None:
            self._write_db_cache(symbol, df)
            self._update_freshness("yfinance", "GREEN")
            return df

        logger.warning(f"[{symbol}] L1 yfinance failed — trying L2 nsepython")
        self._update_freshness("yfinance", "AMBER", f"yfinance failed for {symbol}")

        # L2 — nsepython
        df = _retry_with_backoff(
            lambda s: self._try_nsepython(s),
            symbol, MAX_RETRY_ATTEMPTS, RETRY_BACKOFF_FACTOR
        )
        if df is not None:
            self._write_db_cache(symbol, df)
            self._update_freshness("nsepython", "GREEN")
            return df

        logger.warning(f"[{symbol}] L2 nsepython failed — trying L3 DB cache")
        self._update_freshness("nsepython", "AMBER", f"nsepython failed for {symbol}")

        # L3 — DB cache
        df = self._try_db_cache(symbol)
        if df is not None:
            self._update_freshness("db_cache", "AMBER", f"Serving stale cache for {symbol}")
            return df

        # All sources failed → SIGNAL FREEZE
        self._freeze_signal(symbol)
        return None

    def fetch_multiple(self, symbols: list[str], days: int = 365) -> dict[str, Optional[pd.DataFrame]]:
        """Fetch OHLCV for multiple symbols."""
        return {sym: self.fetch_ohlcv(sym, days) for sym in symbols}

    def check_data_freshness(self, source: str) -> dict:
        """Return freshness status for a source."""
        row = execute_one("SELECT * FROM data_freshness WHERE source=?", (source,))
        if not row:
            return {"source": source, "status": "UNKNOWN", "consecutive_failures": 0}
        return dict(row)

    # -------------------------------------------------------------------------
    # PRIVATE — Source Implementations
    # -------------------------------------------------------------------------
    def _try_yfinance(self, symbol: str, days: int = 365) -> Optional[pd.DataFrame]:
        try:
            import yfinance as yf
            # NSE symbols use .NS suffix
            ticker = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
            end   = datetime.now()
            start = end - timedelta(days=days)
            df = yf.download(
                ticker, start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                progress=False, auto_adjust=True,
                timeout=REQUEST_TIMEOUT_SECS
            )
            if df is None or df.empty:
                return None
            df.columns = [c.lower() for c in df.columns]
            return DataValidator.validate_ohlcv(df)
        except Exception as e:
            logger.warning(f"yfinance [{symbol}]: {e}")
            return None

    def _try_nsepython(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            import nsepython as nse
            start = (datetime.now() - timedelta(days=365)).strftime("%d-%m-%Y")
            end   = datetime.now().strftime("%d-%m-%Y")
            data  = nse.equity_history(symbol, "EQ", start, end)
            if data is None or data.empty:
                return None
            data.columns = [c.lower() for c in data.columns]
            # nsepython column mapping
            col_map = {"ch_timestamp": "date", "ch_opening_price": "open",
                       "ch_trade_high_price": "high", "ch_trade_low_price": "low",
                       "ch_closing_price": "close", "ch_tot_trd_qnty": "volume"}
            data = data.rename(columns=col_map)
            if "date" in data.columns:
                data["date"] = pd.to_datetime(data["date"])
                data = data.set_index("date")
            return DataValidator.validate_ohlcv(data)
        except Exception as e:
            logger.warning(f"nsepython [{symbol}]: {e}")
            return None

    def _try_db_cache(self, symbol: str) -> Optional[pd.DataFrame]:
        """Read last 365 days of cached OHLCV from SQLite."""
        try:
            import sqlite3
            from config.settings import DB_PATH
            with sqlite3.connect(DB_PATH) as conn:
                stock_id_row = conn.execute(
                    "SELECT id FROM stocks WHERE symbol=?", (symbol,)
                ).fetchone()
                if not stock_id_row:
                    return None
                df = pd.read_sql(
                    """SELECT date, open, high, low, close, volume
                       FROM ohlcv_cache WHERE stock_id=?
                       ORDER BY date DESC LIMIT 365""",
                    conn, params=(stock_id_row[0],), parse_dates=["date"]
                )
            if df.empty:
                return None
            df = df.set_index("date").sort_index()
            logger.warning(f"[L3] Serving stale DB cache for {symbol}")
            return df
        except Exception as e:
            logger.error(f"DB cache read failed [{symbol}]: {e}")
            return None

    def _write_db_cache(self, symbol: str, df: pd.DataFrame):
        """Upsert validated OHLCV into DB cache."""
        try:
            stock_row = execute_one("SELECT id FROM stocks WHERE symbol=?", (symbol,))
            if not stock_row:
                return
            sid = stock_row["id"]
            rows = []
            for dt, row in df.iterrows():
                rows.append((
                    sid, str(dt.date() if hasattr(dt, "date") else dt),
                    float(row.get("open", 0)),  float(row.get("high", 0)),
                    float(row.get("low", 0)),   float(row["close"]),
                    int(row.get("volume", 0))
                ))
            execute_many(
                """INSERT INTO ohlcv_cache(stock_id,date,open,high,low,close,volume)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(stock_id,date) DO UPDATE SET
                   close=excluded.close, volume=excluded.volume,
                   high=MAX(high,excluded.high), low=MIN(low,excluded.low)""",
                rows
            )
        except Exception as e:
            logger.warning(f"DB cache write failed [{symbol}]: {e}")

    def _freeze_signal(self, symbol: str):
        """Insert CRITICAL alert and mark source RED."""
        try:
            execute_write(
                "INSERT INTO alerts(alert_type,message,priority) VALUES(?,?,?)",
                ("SIGNAL_FROZEN",
                 f"Signal frozen for {symbol}: all data sources unavailable.",
                 "HIGH")
            )
            self._update_freshness("all_sources", "RED",
                                   f"All sources failed for {symbol}")
            logger.error(f"[SIGNAL_FREEZE] {symbol} — all data sources unavailable")
        except Exception as e:
            logger.error(f"Could not freeze signal for {symbol}: {e}")

    def _update_freshness(self, source: str, status: str, error: Optional[str] = None):
        try:
            execute_write(
                """INSERT INTO data_freshness(source,last_updated,status,error_message,consecutive_failures)
                   VALUES(?,datetime('now'),?,?,?)
                   ON CONFLICT(source) DO UPDATE SET
                   last_updated=excluded.last_updated,
                   status=excluded.status,
                   error_message=excluded.error_message,
                   consecutive_failures = CASE
                       WHEN excluded.status='RED'
                           THEN data_freshness.consecutive_failures + 1
                       ELSE 0 END""",
                (source, status, error, 1 if status == "RED" else 0)
            )
        except Exception as e:
            logger.debug(f"Freshness update failed: {e}")
