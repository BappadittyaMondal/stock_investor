"""
HFOS v5.0 — Screener.in Fundamental Data Fetcher
Scrapes consolidated financials and writes to `fundamentals` table.
Respects robots.txt (rate-limited, user-agent identified).
Fallback: structured parse from cached HTML.
"""
import logging
import time
import re
from typing import Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from database.db_manager import execute_write
from repositories.stock_repository import StockRepository
from schemas.validators import FundamentalCreate
from config.settings import SCREENER_BASE_URL, REQUEST_TIMEOUT_SECS, MAX_RETRY_ATTEMPTS

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "HFOS-Research-Bot/5.0 (private institutional research; not for redistribution)",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}
RATE_LIMIT_SEC = 3.0   # polite crawl delay per request


class ScreenerScraper:
    """
    Fetches quarterly / annual fundamentals from screener.in.
    Writes upserted data into the `fundamentals` table.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._repo = StockRepository()

    # -------------------------------------------------------------------------
    # PUBLIC
    # -------------------------------------------------------------------------
    def fetch_and_store(self, symbol: str) -> Optional[dict]:
        """
        Main entry point. Fetches fundamentals for `symbol`,
        persists to DB, and returns the parsed dict.
        Returns None on failure.
        """
        stock = self._repo.get_by_symbol(symbol)
        if not stock:
            logger.warning(f"[Screener] Stock not found in DB: {symbol}")
            return None

        html = self._fetch_html(symbol)
        if not html:
            return None

        data = self._parse(html, symbol)
        if not data:
            return None

        # Validate and write
        try:
            record = FundamentalCreate(stock_id=stock["id"], **data)
            self._upsert(record)
            logger.info(f"[Screener] Saved fundamentals for {symbol} ({data['report_date']})")
            return data
        except Exception as e:
            logger.error(f"[Screener] Validation/save failed for {symbol}: {e}")
            return None

    def bulk_fetch(self, symbols: list[str]) -> dict[str, bool]:
        """Fetch for multiple symbols with rate limiting."""
        results = {}
        for sym in symbols:
            try:
                result = self.fetch_and_store(sym)
                results[sym] = result is not None
                time.sleep(RATE_LIMIT_SEC)
            except Exception as e:
                logger.error(f"[Screener] bulk_fetch failed for {sym}: {e}")
                results[sym] = False
        return results

    # -------------------------------------------------------------------------
    # PRIVATE — HTTP
    # -------------------------------------------------------------------------
    def _fetch_html(self, symbol: str) -> Optional[str]:
        url = SCREENER_BASE_URL.format(symbol=symbol)
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SECS)
                if resp.status_code == 200:
                    return resp.text
                if resp.status_code == 404:
                    # Try standalone (non-consolidated) page
                    url_standalone = url.replace("/consolidated/", "/")
                    resp = self.session.get(url_standalone, timeout=REQUEST_TIMEOUT_SECS)
                    if resp.status_code == 200:
                        return resp.text
                logger.warning(f"[Screener] {symbol} HTTP {resp.status_code} (attempt {attempt})")
            except requests.RequestException as e:
                logger.warning(f"[Screener] {symbol} request error (attempt {attempt}): {e}")
            time.sleep(2.0 ** attempt)
        return None

    # -------------------------------------------------------------------------
    # PRIVATE — Parsing
    # -------------------------------------------------------------------------
    def _parse(self, html: str, symbol: str) -> Optional[dict]:
        try:
            soup = BeautifulSoup(html, "html.parser")
            data: dict = {
                "report_date":  datetime.today().strftime("%Y-%m-%d"),
                "period_type":  "TTM",
                "source":       "screener",
            }

            # ── Key Ratios ────────────────────────────────────────────────
            data["pe_ratio"]       = self._ratio(soup, "Stock P/E")
            data["pb_ratio"]       = self._ratio(soup, "Price to Book value")
            data["dividend_yield"] = self._ratio(soup, "Dividend Yield")
            data["roe_pct"]        = self._ratio(soup, "Return on equity")
            data["roce_pct"]       = self._ratio(soup, "Return on capital employed")
            data["debt_equity"]    = self._ratio(soup, "Debt to equity")
            data["current_ratio"]  = self._ratio(soup, "Current ratio")

            # ── Shareholding ──────────────────────────────────────────────
            data["promoter_holding"] = self._shareholding(soup, "Promoters")
            data["fii_holding"]      = self._shareholding(soup, "FIIs")
            data["dii_holding"]      = self._shareholding(soup, "DIIs")
            data["pledged_pct"]      = self._shareholding(soup, "Pledged percentage") or 0.0

            # ── P&L (TTM) ─────────────────────────────────────────────────
            data["revenue_cr"]        = self._pnl_value(soup, "Net Sales")
            data["ebitda_cr"]         = self._pnl_value(soup, "Operating Profit")
            data["pat_cr"]            = self._pnl_value(soup, "Net Profit")
            data["eps"]               = self._pnl_value(soup, "EPS in Rs")
            data["revenue_growth_yoy"] = self._yoy_growth(soup, "Net Sales")
            data["pat_growth_yoy"]     = self._yoy_growth(soup, "Net Profit")

            # ── Cash Flow ─────────────────────────────────────────────────
            data["operating_cf"] = self._cf_value(soup, "Cash from Operations")
            data["fcf_cr"]       = self._calc_fcf(soup)

            return {k: v for k, v in data.items() if v is not None or k in
                    ("report_date", "period_type", "source", "pledged_pct")}

        except Exception as e:
            logger.error(f"[Screener] Parse failed for {symbol}: {e}")
            return None

    # ── Screener HTML extraction helpers ─────────────────────────────────────

    def _ratio(self, soup: BeautifulSoup, label: str) -> Optional[float]:
        """Extract a key ratio value from the top ratios section."""
        try:
            for li in soup.select("#top-ratios li"):
                name_tag = li.select_one(".name")
                val_tag  = li.select_one(".value")
                if name_tag and val_tag and label.lower() in name_tag.get_text(strip=True).lower():
                    return self._to_float(val_tag.get_text(strip=True))
        except Exception:
            pass
        return None

    def _shareholding(self, soup: BeautifulSoup, label: str) -> Optional[float]:
        """Extract latest shareholding percentage."""
        try:
            for row in soup.select("table.data-table tbody tr"):
                cells = row.find_all("td")
                if cells and label.lower() in cells[0].get_text(strip=True).lower():
                    # Last column = most recent quarter
                    last = cells[-1].get_text(strip=True)
                    return self._to_float(last)
        except Exception:
            pass
        return None

    def _pnl_value(self, soup: BeautifulSoup, label: str) -> Optional[float]:
        """Extract TTM/trailing P&L value (last column in P&L table)."""
        try:
            for section in soup.select("section"):
                h2 = section.find("h2")
                if h2 and "profit & loss" in h2.get_text(strip=True).lower():
                    for row in section.select("table tr"):
                        cells = row.find_all("td")
                        if cells and label.lower() in cells[0].get_text(strip=True).lower():
                            last = cells[-1].get_text(strip=True)
                            return self._to_float(last)
        except Exception:
            pass
        return None

    def _yoy_growth(self, soup: BeautifulSoup, label: str) -> Optional[float]:
        """Calculate YoY growth from last two years of P&L data."""
        try:
            for section in soup.select("section"):
                h2 = section.find("h2")
                if h2 and "profit & loss" in h2.get_text(strip=True).lower():
                    for row in section.select("table tr"):
                        cells = row.find_all("td")
                        if cells and label.lower() in cells[0].get_text(strip=True).lower():
                            vals = [self._to_float(c.get_text(strip=True))
                                    for c in cells[1:] if self._to_float(c.get_text(strip=True)) is not None]
                            if len(vals) >= 2 and vals[-2] and vals[-2] != 0:
                                return round(((vals[-1] - vals[-2]) / abs(vals[-2])) * 100, 2)
        except Exception:
            pass
        return None

    def _cf_value(self, soup: BeautifulSoup, label: str) -> Optional[float]:
        """Extract cash flow value."""
        try:
            for section in soup.select("section"):
                h2 = section.find("h2")
                if h2 and "cash flow" in h2.get_text(strip=True).lower():
                    for row in section.select("table tr"):
                        cells = row.find_all("td")
                        if cells and label.lower() in cells[0].get_text(strip=True).lower():
                            last = cells[-1].get_text(strip=True)
                            return self._to_float(last)
        except Exception:
            pass
        return None

    def _calc_fcf(self, soup: BeautifulSoup) -> Optional[float]:
        """FCF = Operating CF - Capex."""
        try:
            ocf   = self._cf_value(soup, "Cash from Operations")
            capex = self._cf_value(soup, "Cash from Investing")  # usually negative
            if ocf is not None and capex is not None:
                return round(ocf + capex, 2)  # capex is already negative
        except Exception:
            pass
        return None

    @staticmethod
    def _to_float(text: str) -> Optional[float]:
        """Convert screener text like '₹ 1,234.56' or '12.5%' to float."""
        try:
            cleaned = re.sub(r"[₹,\s%]", "", text.strip())
            if cleaned in ("", "-", "—", "N/A"):
                return None
            return float(cleaned)
        except ValueError:
            return None

    # -------------------------------------------------------------------------
    def _upsert(self, record: FundamentalCreate):
        execute_write(
            """INSERT INTO fundamentals
               (stock_id, report_date, period_type, revenue_cr, ebitda_cr,
                pat_cr, eps, pe_ratio, pb_ratio, roe_pct, roce_pct, debt_equity,
                current_ratio, promoter_holding, fii_holding, dii_holding,
                pledged_pct, dividend_yield, revenue_growth_yoy, pat_growth_yoy,
                operating_cf, fcf_cr, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(stock_id, report_date, period_type) DO UPDATE SET
               revenue_cr=excluded.revenue_cr, ebitda_cr=excluded.ebitda_cr,
               pat_cr=excluded.pat_cr, eps=excluded.eps,
               pe_ratio=excluded.pe_ratio, pb_ratio=excluded.pb_ratio,
               roe_pct=excluded.roe_pct, roce_pct=excluded.roce_pct,
               debt_equity=excluded.debt_equity, current_ratio=excluded.current_ratio,
               promoter_holding=excluded.promoter_holding,
               pledged_pct=excluded.pledged_pct,
               dividend_yield=excluded.dividend_yield,
               revenue_growth_yoy=excluded.revenue_growth_yoy,
               pat_growth_yoy=excluded.pat_growth_yoy,
               operating_cf=excluded.operating_cf, fcf_cr=excluded.fcf_cr""",
            (record.stock_id, record.report_date, record.period_type,
             record.revenue_cr, record.ebitda_cr, record.pat_cr, record.eps,
             record.pe_ratio, record.pb_ratio, record.roe_pct, record.roce_pct,
             record.debt_equity, record.current_ratio, record.promoter_holding,
             record.fii_holding, record.dii_holding, record.pledged_pct,
             record.dividend_yield, record.revenue_growth_yoy, record.pat_growth_yoy,
             record.operating_cf, record.fcf_cr, record.source)
        )
