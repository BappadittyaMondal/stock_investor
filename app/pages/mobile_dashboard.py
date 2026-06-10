"""HFOS v5.0 — Mobile Dashboard (PWA)"""
import streamlit as st
from database.db_manager import execute_query

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
    st.markdown("""
    <style>
        .stApp { max-width: 100vw; overflow-x: hidden; }
        .mobile-card { background: #1a2035; padding: 15px; border-radius: 12px; border: 1px solid #2d3f6e; margin-bottom: 12px; }
        .mobile-header { font-size: 1.2rem; font-weight: 600; color: #e2e8f0; margin-bottom: 8px; }
        .mobile-stat { font-size: 1.5rem; font-weight: 700; color: #38bdf8; }
        .signal-badge { background: #0f1629; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📱 HFOS Mobile")
    
    # AI Summary
    st.markdown("""
    <div class="mobile-card">
        <div class="mobile-header">🤖 Executive Summary</div>
        <div style="color: #94a3b8; font-size: 0.9rem;">
            Market Regime is <span style="color:#fbbf24">Neutral</span>. Portfolio remains stable with a +1.2% daily gain. 
            Tech sector showing strong momentum. 2 new STRONG_BUY signals detected.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Market & Portfolio Quick Stats
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="mobile-card">
            <div style="font-size:0.8rem; color:#94a3b8;">Nifty 50</div>
            <div class="mobile-stat" style="color:#00ff88;">+1.1%</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="mobile-card">
            <div style="font-size:0.8rem; color:#94a3b8;">Portfolio</div>
            <div class="mobile-stat" style="color:#00ff88;">₹2.4M</div>
        </div>
        """, unsafe_allow_html=True)

    # Today's Signals
    st.markdown("#### 🚀 Top Signals")
    signals = execute_query("SELECT s.symbol, sc.signal, sc.alpha_score FROM scores sc JOIN stocks s ON sc.stock_id=s.id WHERE sc.signal IN ('STRONG_BUY','BUY') ORDER BY sc.alpha_score DESC LIMIT 5")
    if signals:
        for s in signals:
            color = "#00ff88" if s['signal'] == "STRONG_BUY" else "#4ade80"
            st.markdown(f"""
            <div class="mobile-card" style="display:flex; justify-content:space-between; align-items:center;">
                <div style="font-weight:600;">{s['symbol']}</div>
                <div>
                    <span class="signal-badge" style="color:{color}; border: 1px solid {color}">{s['signal']}</span>
                    <span style="color:#e2e8f0; margin-left: 10px;">{s['alpha_score']:.1f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No buy signals today.")
        
    # Mobile Bottom Navigation (Simulated via HTML overlay)
    st.markdown("""
    <div style="position: fixed; bottom: 0; left: 0; width: 100%; background: #0f172a; border-top: 1px solid #1e293b; display: flex; justify-content: space-around; padding: 10px 0; z-index: 9999;">
        <a href="?nav=mobile" style="text-decoration:none; color:#38bdf8; font-size:1.5rem; text-align:center;"><div>🏠</div><div style="font-size:0.6rem;">Home</div></a>
        <a href="?nav=scanner" style="text-decoration:none; color:#94a3b8; font-size:1.5rem; text-align:center;"><div>🔍</div><div style="font-size:0.6rem;">Scan</div></a>
        <a href="?nav=portfolio" style="text-decoration:none; color:#94a3b8; font-size:1.5rem; text-align:center;"><div>📊</div><div style="font-size:0.6rem;">Port</div></a>
        <a href="?nav=watchlists" style="text-decoration:none; color:#94a3b8; font-size:1.5rem; text-align:center;"><div>⭐</div><div style="font-size:0.6rem;">Watch</div></a>
    </div>
    <div style="height: 60px;"></div>
    """, unsafe_allow_html=True)
