"""
HFOS v5.0 — Scanner Service
Orchestrates all 8 engines to score the full universe.
Produces ranked signals, watchlist updates, and portfolio triggers.
"""
import logging
from datetime import datetime
from typing import Optional

from engines.scoring.alpha_engine      import AlphaEngine
from engines.fundamental.fundamental_engine import FundamentalEngine
from engines.technical.technical_engine     import TechnicalEngine
from engines.risk.risk_engine               import RiskEngine
from engines.sector.sector_engine           import SectorEngine
from engines.news.news_engine               import NewsEngine
from engines.macro.macro_engine             import MacroEngine
from engines.geo.geo_engine                 import GeoEngine
from services.data_fetcher                  import DataFetcher
from services.alert_service                 import AlertService
from database.db_manager import execute_query, execute_write, execute_one

logger = logging.getLogger(__name__)


class ScannerService:
    """
    Full universe scan → scores → signals → watchlists → alerts.
    """

    def __init__(self):
        self.alpha     = AlphaEngine()
        self.fund_eng  = FundamentalEngine()
        self.tech_eng  = TechnicalEngine()
        self.risk_eng  = RiskEngine()
        self.sec_eng   = SectorEngine()
        self.news_eng  = NewsEngine()
        self.macro_eng = MacroEngine()
        self.geo_eng   = GeoEngine()
        self.fetcher   = DataFetcher()
        self.alerts    = AlertService()

    # -------------------------------------------------------------------------
    def scan_universe(self, limit: Optional[int] = None) -> list[dict]:
        """
        Score all active stocks. Returns sorted list of scored stocks.
        """
        stocks = execute_query(
            """SELECT id, symbol, name, sector, market_cap_cr,
                      asm_flag, gsm_flag, pledge_pct, avg_daily_vol
               FROM stocks WHERE is_active=1
               ORDER BY market_cap_cr DESC NULLS LAST"""
        )
        if limit:
            stocks = stocks[:limit]

        logger.info(f"Starting universe scan: {len(stocks)} stocks")

        # Macro + Geo are market-wide — compute once
        macro_score = self.macro_eng.score()
        results = []

        for stock in stocks:
            try:
                result = self._score_stock(dict(stock), macro_score)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Score failed [{stock['symbol']}]: {e}")

        # Sort by alpha descending
        results.sort(key=lambda x: x["alpha_score"], reverse=True)
        logger.info(f"Universe scan complete. Top signal: "
                    f"{results[0]['symbol']} α={results[0]['alpha_score']}" if results else "No results")
        return results

    def scan_single(self, symbol: str) -> Optional[dict]:
        """Score a single stock by symbol."""
        row = execute_one(
            """SELECT id, symbol, name, sector, market_cap_cr,
                      asm_flag, gsm_flag, pledge_pct, avg_daily_vol
               FROM stocks WHERE symbol=? COLLATE NOCASE""",
            (symbol,)
        )
        if not row:
            logger.warning(f"Stock not found: {symbol}")
            return None
        macro_score = self.macro_eng.score()
        return self._score_stock(dict(row), macro_score)

    # -------------------------------------------------------------------------
    def _score_stock(self, stock: dict, macro_score: float) -> Optional[dict]:
        sym    = stock["symbol"]
        sector = stock.get("sector") or "Default"

        # Fetch OHLCV (with fallback chain)
        df = self.fetcher.fetch_ohlcv(sym)
        if df is None or df.empty:
            logger.warning(f"[{sym}] No OHLCV — skipping")
            return None

        # Run all engines
        scores = {
            "fundamental_score": self.fund_eng.score_from_db(stock["id"]),
            "technical_score":   self.tech_eng.score(df, sym),
            "risk_score":        self.risk_eng.score(stock, df),
            "sector_score":      self.sec_eng.score(sector, stock),
            "news_score":        self.news_eng.score(sym, stock.get("name", "")),
            "macro_score":       macro_score,
            "policy_score":      self._policy_score(sector, sym),
            "geo_score":         self.geo_eng.score(sector),
        }

        alpha  = self.alpha.calculate(scores)
        signal, confidence = self.alpha.classify(alpha)

        # Get last close
        last_close = float(df["close"].iloc[-1])

        result = {
            **stock,
            **scores,
            "alpha_score":  alpha,
            "signal":       signal,
            "confidence":   confidence,
            "last_close":   last_close,
            "scanned_at":   datetime.now().isoformat(),
        }

        # Persist score to DB
        self._save_score(stock["id"], scores, alpha, signal, confidence)

        # Trigger alerts for strong signals
        if signal in ("STRONG_BUY", "BUY"):
            self._check_and_alert(result, last_close)

        return result

    def _policy_score(self, sector: str, symbol: str) -> float:
        from engines.policy.policy_engine import PolicyEngine
        return PolicyEngine().score(sector, symbol)

    def _save_score(self, stock_id: int, scores: dict,
                    alpha: float, signal: str, confidence: str):
        try:
            execute_write(
                """INSERT INTO scores
                   (stock_id, fundamental_score, technical_score, sector_score,
                    risk_score, policy_score, news_score, macro_score, geo_score,
                    alpha_score, signal, confidence)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (stock_id,
                 scores["fundamental_score"], scores["technical_score"],
                 scores["sector_score"],      scores["risk_score"],
                 scores["policy_score"],      scores["news_score"],
                 scores["macro_score"],       scores["geo_score"],
                 alpha, signal, confidence)
            )
        except Exception as e:
            logger.warning(f"Score save failed for stock_id={stock_id}: {e}")

    def _check_and_alert(self, result: dict, price: float):
        """Send signal alert if high-conviction and eligible."""
        from services.portfolio_service import PortfolioService
        ps = PortfolioService()
        sl = ps.suggest_stop_loss(price)
        target = price + (price - sl) * 2.5

        eligible, reason = self.alpha.is_portfolio_eligible(
            result, result["alpha_score"],
            ps.get_sector_exposure().get(result.get("sector", ""), 0.0)
        )
        if eligible:
            self.alerts.send_signal(
                symbol=result["symbol"],
                signal=result["signal"],
                alpha=result["alpha_score"],
                price=price,
                stop_loss=sl,
                target=target,
            )
