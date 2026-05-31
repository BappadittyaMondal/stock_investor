"""
HFOS v5.0 — Unit Tests: Screener Scraper (no network)
"""
import pytest
from unittest.mock import patch, MagicMock
from services.screener_scraper import ScreenerScraper


@pytest.fixture
def scraper():
    with patch("services.screener_scraper.StockRepository"):
        return ScreenerScraper()


class TestScreenerScraperParsing:
    """Test HTML parsing without network calls."""

    SAMPLE_HTML = """
    <html><body>
      <section id="top-ratios">
        <ul>
          <li><span class="name">Stock P/E</span><span class="value">22.5</span></li>
          <li><span class="name">Price to Book value</span><span class="value">3.2</span></li>
          <li><span class="name">Return on equity</span><span class="value">18.4</span></li>
          <li><span class="name">Return on capital employed</span><span class="value">21.1</span></li>
          <li><span class="name">Debt to equity</span><span class="value">0.42</span></li>
          <li><span class="name">Dividend Yield</span><span class="value">1.2%</span></li>
          <li><span class="name">Current ratio</span><span class="value">1.8</span></li>
        </ul>
      </section>
    </body></html>
    """

    def test_ratio_extraction(self, scraper):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self.SAMPLE_HTML, "html.parser")
        assert scraper._ratio(soup, "Stock P/E") == 22.5
        assert scraper._ratio(soup, "Price to Book value") == 3.2
        assert scraper._ratio(soup, "Return on equity") == 18.4
        assert scraper._ratio(soup, "Debt to equity") == 0.42
        assert scraper._ratio(soup, "Dividend Yield") == 1.2

    def test_missing_ratio_returns_none(self, scraper):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        assert scraper._ratio(soup, "Stock P/E") is None

    def test_to_float_currency(self, scraper):
        assert scraper._to_float("₹ 1,234.56") == 1234.56

    def test_to_float_percent(self, scraper):
        assert scraper._to_float("12.5%") == 12.5

    def test_to_float_dash(self, scraper):
        assert scraper._to_float("-") is None

    def test_to_float_blank(self, scraper):
        assert scraper._to_float("") is None

    def test_to_float_na(self, scraper):
        assert scraper._to_float("N/A") is None

    def test_fetch_and_store_missing_stock(self, scraper):
        scraper._repo.get_by_symbol.return_value = None
        result = scraper.fetch_and_store("UNKNOWN")
        assert result is None

    def test_fetch_html_retries_on_404(self, scraper):
        mock_resp_404 = MagicMock(status_code=404)
        mock_resp_200 = MagicMock(status_code=200, text="<html></html>")
        scraper.session.get = MagicMock(side_effect=[mock_resp_404, mock_resp_200])
        result = scraper._fetch_html("TESTCO")
        assert result == "<html></html>"
        assert scraper.session.get.call_count == 2

    def test_fetch_html_all_fail_returns_none(self, scraper):
        mock_resp = MagicMock(status_code=500)
        scraper.session.get = MagicMock(return_value=mock_resp)
        with patch("time.sleep"):  # speed up test
            result = scraper._fetch_html("FAILCO")
        assert result is None
