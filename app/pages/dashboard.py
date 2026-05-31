"""
HFOS v5.0 — Dashboard Page (Command Center)
Decision-first institutional layout.
"""
import streamlit as st
import pandas as pd
from database.db_manager import execute_query, execute_one

def render():
    st.title("🏛️ Market Command Center")
    st.caption("Decision velocity optimized. What matters right now.")

    # ── 1. MARKET COMMAND CENTER (Macro / Regime) ──────────────────────────
    st.subheader("Market State")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # In a real scenario, these would pull from MacroEngine/DB.
    # For now, we simulate the state from recent data or defaults.
    geo_risk = execute_one("SELECT COUNT(*) as c FROM geo_events WHERE severity IN ('CRITICAL','HIGH')")
    risk_state = "🟡 Neutral" if not geo_risk or geo_risk["c"] == 0 else "🔴 Risk-Off"
    
    with col1:
        st.metric("Nifty Trend", "🟢 Bullish", "+1.2% (1W)")
    with col2:
        st.metric("Bank Nifty", "🟡 Neutral", "-0.4% (1W)")
    with col3:
        st.metric("Market Breadth", "🟢 Positive", "2.1 A/D")
    with col4:
        st.metric("FII/DII Flow", "🟢 Net Buy", "₹2,400 Cr")
    with col5:
        st.metric("Risk Regime", risk_state)
        
    st.divider()

    # ── 2. TODAY'S ACTIONS (Decision Matrix) ───────────────────────────────
    st.subheader("⚡ Action Matrix")
    
    # Fetch recent scored stocks for the matrix
    recent_scores = execute_query(
        """SELECT s.symbol, sc.signal, sc.alpha_score 
           FROM scores sc JOIN stocks s ON sc.stock_id=s.id
           WHERE sc.scored_at >= date('now', '-3 day')
           ORDER BY sc.alpha_score DESC"""
    )
    
    df_actions = pd.DataFrame([dict(r) for r in recent_scores]) if recent_scores else pd.DataFrame(columns=["symbol","signal","alpha_score"])
    
    c_buy, c_watch, c_reduce, c_avoid = st.columns(4)
    
    with c_buy:
        st.markdown("### 🟢 BUY NOW")
        buys = df_actions[df_actions["signal"].isin(["STRONG_BUY", "BUY"])].head(10)
        for _, row in buys.iterrows():
            st.button(f"{row['symbol']} ({row['alpha_score']})", key=f"b_{row['symbol']}", use_container_width=True)
        if buys.empty: st.caption("No immediate buys.")
            
    with c_watch:
        st.markdown("### 🟡 WATCH")
        watches = df_actions[df_actions["signal"] == "ACCUMULATE"].head(10)
        for _, row in watches.iterrows():
            st.button(f"{row['symbol']} ({row['alpha_score']})", key=f"w_{row['symbol']}", use_container_width=True)
        if watches.empty: st.caption("No watch items.")

    with c_reduce:
        st.markdown("### 🟠 REDUCE")
        # For simulation, REDUCE might be WATCH or lower for things we hold
        reduces = df_actions[df_actions["signal"] == "WATCH"].head(10)
        for _, row in reduces.iterrows():
            st.button(f"{row['symbol']} ({row['alpha_score']})", key=f"r_{row['symbol']}", use_container_width=True)
        if reduces.empty: st.caption("Nothing to reduce.")
            
    with c_avoid:
        st.markdown("### 🔴 AVOID")
        avoids = df_actions[df_actions["signal"] == "REJECT"].head(10)
        for _, row in avoids.iterrows():
            st.button(f"{row['symbol']} ({row['alpha_score']})", key=f"a_{row['symbol']}", use_container_width=True)
        if avoids.empty: st.caption("No avoids listed.")

    st.divider()

    # ── 3. ALPHA LEADERBOARD ───────────────────────────────────────────────
    st.subheader("🏆 Alpha Leaderboard")
    
    leaderboard = execute_query(
        """SELECT s.symbol as Ticker, s.name as Company, sc.alpha_score as "Alpha Score",
                  sc.confidence as Conviction, s.sector as Sector,
                  (sc.fundamental_score + sc.technical_score)/2 as "Base Edge"
           FROM scores sc JOIN stocks s ON sc.stock_id=s.id
           WHERE sc.scored_at >= date('now', '-3 day')
           ORDER BY sc.alpha_score DESC LIMIT 50"""
    )
    
    if leaderboard:
        df_lb = pd.DataFrame([dict(r) for r in leaderboard])
        df_lb["Risk Grade"] = df_lb["Alpha Score"].apply(lambda x: "Low" if x > 75 else "Med" if x > 50 else "High")
        df_lb["Expected Upside"] = df_lb["Alpha Score"].apply(lambda x: f"{x/2:.1f}%" if x > 50 else "N/A")
        
        # Format the dataframe for display
        df_display = df_lb[["Ticker", "Company", "Alpha Score", "Conviction", "Risk Grade", "Sector", "Expected Upside"]]
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Alpha Score": st.column_config.ProgressColumn("Alpha Score", min_value=0, max_value=100, format="%.1f")
            }
        )
    else:
        st.info("Scanner has not generated scores yet. Run Universe Scanner.")

    # ── Floating Action Copilot Button ─────────────────────────────────────
    st.markdown("""
    <div style="position: fixed; bottom: 30px; right: 30px; z-index: 9999;">
        <a href="?nav=ai_copilot" target="_self" style="background-color: #2563eb; color: white; padding: 15px; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.5); text-decoration: none; font-size: 24px;">🤖</a>
    </div>
    """, unsafe_allow_html=True)
