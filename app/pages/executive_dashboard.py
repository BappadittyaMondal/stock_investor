"""HFOS v5.0 — Executive Dashboard"""
import streamlit as st

def render():
    st.title("👔 Executive Dashboard")
    st.caption("High-level portfolio oversight for Family Offices & PMs")
    
    st.divider()

    # Executive Overview
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total AUM", "₹24.5 Cr", "+₹1.2 Cr (YTD)")
    c2.metric("Portfolio Value", "₹18.2 Cr", "Active Deployed")
    c3.metric("Cash Reserve", "₹6.3 Cr", "25.7% of AUM")
    c4.metric("Alpha Generated", "4.2%", "vs Nifty 500")

    st.divider()

    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("🤖 Executive Briefing")
        st.info("""
        **Market Regime:** Neutral-Bullish. FII flows remain positive but macro volatility limits aggressive deployment.
        
        **Portfolio Status:** Stable. Max drawdown controlled at -4.2%. Sector exposure is slightly overweight in IT (22%).
        
        **Top Opportunities:** 3 High-Conviction Alpha signals generated in Midcap Auto sector.
        
        **Biggest Risks:** Pending RBI policy announcement tomorrow. Watch interest-rate sensitive holdings.
        
        **Recommended Action:** Deploy 5% of cash reserves into Midcap Auto. Hold hedges steady.
        """)

    with col_right:
        st.subheader("⚠️ Risk Exposure")
        st.markdown("""
        <div style="background: #1a2035; padding: 15px; border-radius: 8px; border: 1px solid #2d3f6e;">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:#94a3b8;">Portfolio Beta</span>
                <span style="color:#00ff88; font-weight:bold;">0.85</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:#94a3b8;">Max Sector Wt.</span>
                <span style="color:#fbbf24; font-weight:bold;">22% (IT)</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:#94a3b8;">ASM/GSM Flags</span>
                <span style="color:#00ff88; font-weight:bold;">0</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="color:#94a3b8;">Avg Volatility</span>
                <span style="color:#38bdf8; font-weight:bold;">1.2%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
