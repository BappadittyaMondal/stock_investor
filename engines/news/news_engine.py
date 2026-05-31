"""
HFOS v5.0 — News Engine
Sentiment scoring from RSS feeds (PIB, RBI, SEBI, MoneyControl, ET Markets).
Returns news_score 0-100 (higher = more positive sentiment).
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
import feedparser
from database.db_manager import execute_write, execute_query
from config.settings import (
    PIB_RSS_URL, RBI_RSS_URL, SEBI_RSS_URL
)

logger = logging.getLogger(__name__)

RSS_FEEDS: list[dict] = [
    {"name": "PIB",         "url": PIB_RSS_URL,  "type": "government"},
    {"name": "RBI",         "url": RBI_RSS_URL,  "type": "central_bank"},
    {"name": "SEBI",        "url": SEBI_RSS_URL, "type": "regulator"},
    {"name": "ET_Markets",  "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "type": "news"},
    {"name": "MoneyControl","url": "https://www.moneycontrol.com/rss/MCtopnews.xml", "type": "news"},
]

# Positive/Negative keyword sets for simple lexicon-based sentiment
POSITIVE_KEYWORDS = {
    "growth", "profit", "record", "surge", "rally", "bullish", "expansion",
    "investment", "boost", "strong", "beat", "outperform", "upgrade",
    "dividend", "buyback", "acquisition", "order", "contract", "approval",
    "capex", "revenue", "positive", "recovery", "momentum", "gains",
}
NEGATIVE_KEYWORDS = {
    "loss", "decline", "fall", "drop", "penalty", "fine", "fraud",
    "downgrade", "selloff", "bearish", "default", "recall", "investigation",
    "sebi", "ban", "suspension", "layoff", "debt", "bankruptcy",
    "miss", "below", "concern", "weak", "slowdown", "risk",
}


class NewsEngine:
    """
    News Score: 0-100
    Aggregates sentiment from multiple RSS feeds over the past 7 days.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def score(self, symbol: str, company_name: str = "") -> float:
        """Fetch recent news and return sentiment score 0-100."""
        try:
            articles = self._fetch_recent_articles(symbol, company_name)
            if not articles:
                return 50.0  # Neutral on no news
            sentiment = self._aggregate_sentiment(articles)
            # Persist to DB
            self._save_news(symbol, articles)
            return round(max(0.0, min(100.0, sentiment)), 2)
        except Exception as e:
            logger.error(f"[{symbol}] NewsEngine error: {e}")
            return 50.0

    def score_from_db(self, stock_id: int, lookback_days: int = 7) -> float:
        """Score from already-stored news items."""
        cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()
        rows = execute_query(
            """SELECT sentiment_score FROM news_items
               WHERE stock_id=? AND published_at > ? AND sentiment_score IS NOT NULL""",
            (stock_id, cutoff)
        )
        if not rows:
            return 50.0
        scores = [r["sentiment_score"] for r in rows]
        avg = sum(scores) / len(scores)  # avg in [-1, 1]
        return round((avg + 1.0) * 50.0, 2)  # convert to [0, 100]

    # -------------------------------------------------------------------------
    def _fetch_recent_articles(self, symbol: str, company_name: str) -> list[dict]:
        articles = []
        cutoff = datetime.now() - timedelta(days=7)
        search_terms = [t.lower() for t in [symbol, company_name] if t]

        for feed_meta in RSS_FEEDS:
            try:
                feed = feedparser.parse(
                    feed_meta["url"],
                    request_headers={"User-Agent": "HFOS/5.0 Research Bot"}
                )
                for entry in feed.entries:
                    title   = getattr(entry, "title", "")
                    summary = getattr(entry, "summary", "")
                    text    = (title + " " + summary).lower()

                    # Check relevance
                    relevant = any(term in text for term in search_terms) if search_terms else True

                    # Parse date
                    pub_struct = getattr(entry, "published_parsed", None)
                    if pub_struct:
                        pub_dt = datetime(*pub_struct[:6])
                        if pub_dt < cutoff:
                            continue
                    else:
                        pub_dt = datetime.now()

                    if relevant or feed_meta["type"] in ("government", "central_bank", "regulator"):
                        articles.append({
                            "title":    title,
                            "summary":  summary,
                            "source":   feed_meta["name"],
                            "pub_date": pub_dt,
                            "relevant": relevant,
                        })
            except Exception as e:
                logger.warning(f"RSS fetch failed [{feed_meta['name']}]: {e}")

        return articles

    def _aggregate_sentiment(self, articles: list[dict]) -> float:
        """Lexicon-based sentiment, returns 0-100."""
        if not articles:
            return 50.0
        sentiments = []
        for art in articles:
            text = (art["title"] + " " + art.get("summary", "")).lower()
            words = set(text.split())
            pos = len(words & POSITIVE_KEYWORDS)
            neg = len(words & NEGATIVE_KEYWORDS)
            total = pos + neg
            if total > 0:
                raw = (pos - neg) / total  # -1 to +1
            else:
                raw = 0.0  # neutral
            sentiments.append(raw)

        if not sentiments:
            return 50.0
        avg = sum(sentiments) / len(sentiments)
        return (avg + 1.0) * 50.0  # convert to [0,100]

    def _save_news(self, symbol: str, articles: list[dict]):
        """Persist news to DB (best effort)."""
        try:
            from database.db_manager import execute_one
            stock = execute_one("SELECT id FROM stocks WHERE symbol=?", (symbol,))
            stock_id = stock["id"] if stock else None

            for art in articles[:20]:  # limit per scan
                text = (art["title"] + " " + art.get("summary","")).lower()
                words = set(text.split())
                pos = len(words & POSITIVE_KEYWORDS)
                neg = len(words & NEGATIVE_KEYWORDS)
                total = pos + neg
                raw_score = (pos - neg) / total if total > 0 else 0.0
                sentiment = "POSITIVE" if raw_score > 0.1 else ("NEGATIVE" if raw_score < -0.1 else "NEUTRAL")

                execute_write(
                    """INSERT OR IGNORE INTO news_items
                       (stock_id, source, title, published_at, sentiment, sentiment_score)
                       VALUES (?,?,?,?,?,?)""",
                    (stock_id, art["source"], art["title"][:500],
                     art["pub_date"].isoformat(), sentiment, round(raw_score, 4))
                )
        except Exception as e:
            logger.debug(f"News DB save failed: {e}")
