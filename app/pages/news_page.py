"""HFOS v5.0 — News & Sentiment Page"""
import streamlit as st
import pandas as pd
from database.db_manager import execute_query
from engines.news.news_engine import NewsEngine


def render():
    try:
        _render_body()
    except Exception as _err:
        import traceback as _tb
        import streamlit as st
        st.error("⚠️ This page encountered an error. Please refresh.")
        from services.auth_service import get_current_user
        _u = get_current_user()
        if _u and _u.get("role") == "ADMIN":
            with st.expander("🔧 Admin Debug: Error Details"):
                st.code(_tb.format_exc())

def _render_body():
    st.title("📰 News & Sentiment")

    col1, col2 = st.columns([3,1])
    with col2:
        if st.button("🔄 Refresh News", key="refresh_news"):
            st.rerun()

    # Sentiment summary
    rows = execute_query(
        """SELECT sentiment, COUNT(*) AS cnt FROM news_items
           WHERE created_at >= datetime('now','-7 day')
           GROUP BY sentiment"""
    )
    if rows:
        col_p, col_n, col_neu = st.columns(3)
        data = {r["sentiment"]: r["cnt"] for r in rows}
        col_p.metric("✅ Positive",  data.get("POSITIVE", 0))
        col_n.metric("❌ Negative",  data.get("NEGATIVE", 0))
        col_neu.metric("➖ Neutral", data.get("NEUTRAL", 0))
        st.divider()

    # Recent news
    st.subheader("Recent Articles (Last 7 Days)")
    news = execute_query(
        """SELECT n.title, n.source, n.sentiment, n.sentiment_score,
                  n.published_at, s.symbol
           FROM news_items n
           LEFT JOIN stocks s ON n.stock_id=s.id
           WHERE n.published_at >= datetime('now','-7 day')
           ORDER BY n.published_at DESC LIMIT 100"""
    )
    if news:
        df = pd.DataFrame([dict(r) for r in news])
        df["published_at"] = pd.to_datetime(df["published_at"]).dt.strftime("%d-%b %H:%M")
        df["sentiment_score"] = df["sentiment_score"].round(3)
        st.dataframe(df.rename(columns={
            "title":"Title","source":"Source","sentiment":"Sentiment",
            "sentiment_score":"Score","published_at":"Published","symbol":"Symbol"
        }), use_container_width=True, hide_index=True)
    else:
        st.info("No news stored yet. Run a scan to fetch and store news.")

    # Manual scan for specific stock
    st.divider()
    st.subheader("Scan News for Symbol")
    with st.form("news_scan_form"):
        sym  = st.text_input("Symbol", placeholder="e.g. WIPRO").upper().strip()
        name = st.text_input("Company name (optional)")
        if st.form_submit_button("Fetch News →") and sym:
            with st.spinner(f"Fetching news for {sym}..."):
                eng   = NewsEngine()
                score = eng.score(sym, name)
            st.metric("News Sentiment Score", f"{score:.1f}/100")
