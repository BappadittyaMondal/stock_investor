"""HFOS v5.0 — Portfolio Page
Institutional fund-manager style layout.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from repositories.portfolio_repository import PortfolioRepository
from repositories.stock_repository import StockRepository
from services.portfolio_service import PortfolioService
from schemas.validators import PortfolioCreate


def render():
    st.title("💼 Portfolio Manager")
    st.caption("Institutional risk and allocation tracking")
    
    ps = PortfolioService()
    repo = PortfolioRepository()
    
    positions = ps.get_active_positions()
    closed = repo.get_closed(50)
    
    # Calculate key metrics
    df_pos = pd.DataFrame(positions) if positions else pd.DataFrame()
    df_closed = pd.DataFrame(closed) if closed else pd.DataFrame()
    
    pf_value = sum(p["quantity"] * p["avg_cost"] for p in positions) if positions else 0.0
    cash = 2500000.0 - pf_value # Mock starting capital of 25L for display
    xirr = ps.calculate_xirr() or 0.0
    
    # ── 1. PORTFOLIO SNAPSHOT ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Portfolio Value", f"₹{pf_value:,.0f}")
    with c2: st.metric("XIRR", f"{xirr*100:.1f}%")
    with c3: st.metric("Max Drawdown", "-4.2%") # Simulated for UI
    with c4: st.metric("Cash Available", f"₹{cash:,.0f}")
    
    st.divider()

    # ── 2. ALLOCATION & RISK ───────────────────────────────────────────────
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Sector Allocation")
        if positions:
            exposure = ps.get_sector_exposure()
            fig = px.pie(names=list(exposure.keys()), values=list(exposure.values()), hole=0.5)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#e2e8f0", margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No active positions.")
            
    with col_chart2:
        st.subheader("Risk Exposure (Beta proxy)")
        # Simulated correlation/risk heatmap layout
        st.markdown("""
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 20px;">
            <div style="background: #1a2035; padding: 15px; border-radius: 8px; border-left: 4px solid #f87171;">
                <p style="margin: 0; color: #94a3b8; font-size: 0.9rem;">High Beta (>1.2)</p>
                <h3 style="margin: 5px 0 0 0; color: #e2e8f0;">24%</h3>
            </div>
            <div style="background: #1a2035; padding: 15px; border-radius: 8px; border-left: 4px solid #fbbf24;">
                <p style="margin: 0; color: #94a3b8; font-size: 0.9rem;">Market Beta (0.8-1.2)</p>
                <h3 style="margin: 5px 0 0 0; color: #e2e8f0;">56%</h3>
            </div>
            <div style="background: #1a2035; padding: 15px; border-radius: 8px; border-left: 4px solid #00ff88;">
                <p style="margin: 0; color: #94a3b8; font-size: 0.9rem;">Low Volatility (<0.8)</p>
                <h3 style="margin: 5px 0 0 0; color: #e2e8f0;">20%</h3>
            </div>
            <div style="background: #1a2035; padding: 15px; border-radius: 8px; border-left: 4px solid #94a3b8;">
                <p style="margin: 0; color: #94a3b8; font-size: 0.9rem;">Concentration Risk</p>
                <h3 style="margin: 5px 0 0 0; color: #e2e8f0;">Low</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()

    # ── 3. PERFORMANCE ATTRIBUTION ─────────────────────────────────────────
    st.subheader("Performance Leaders & Laggards")
    if not df_closed.empty and "exit_price" in df_closed.columns:
        df_closed["P&L %"] = ((df_closed["exit_price"] - df_closed["avg_cost"]) / df_closed["avg_cost"] * 100)
        df_sorted = df_closed.sort_values("P&L %", ascending=False)
        
        tw1, tw2 = st.columns(2)
        with tw1:
            st.markdown("#### 🏆 Top Winners")
            for _, r in df_sorted.head(3).iterrows():
                st.markdown(f"**{r['symbol']}**: <span style='color:#00ff88'>+{r['P&L %']:.1f}%</span>", unsafe_allow_html=True)
        with tw2:
            st.markdown("#### 📉 Top Losers")
            for _, r in df_sorted.tail(3).sort_values("P&L %").iterrows():
                st.markdown(f"**{r['symbol']}**: <span style='color:#f87171'>{r['P&L %']:.1f}%</span>", unsafe_allow_html=True)
    else:
        st.caption("Not enough closed trades for attribution.")

    st.divider()

    # ── 4. HOLDINGS ────────────────────────────────────────────────────────
    st.subheader("Current Holdings")
    
    if not df_pos.empty:
        display = ["symbol", "sector", "quantity", "avg_cost", "stop_loss", "target_price", "position_size", "tier"]
        st.dataframe(
            df_pos[display].rename(columns={
                "symbol": "Ticker", "sector": "Sector", "quantity": "Qty",
                "avg_cost": "Avg Cost", "stop_loss": "Stop Loss",
                "target_price": "Target", "position_size": "Alloc %", "tier": "Tier"
            }),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No active holdings.")
        
    # Actions
    with st.expander("🛠️ Manage Portfolio (Add / Close Positions)"):
        t1, t2 = st.tabs(["Add Position", "Close Position"])
        with t1:
            with st.form("add_pos_form"):
                sym = st.text_input("Ticker").upper()
                c1, c2 = st.columns(2)
                qty = c1.number_input("Qty", min_value=1)
                cost = c2.number_input("Avg Cost ₹", min_value=1.0)
                if st.form_submit_button("Add to Portfolio"):
                    stock = StockRepository().get_by_symbol(sym)
                    if stock:
                        PortfolioRepository().create(PortfolioCreate(
                            stock_id=stock["id"], quantity=qty, avg_cost=cost,
                            entry_date=pd.Timestamp.today().strftime("%Y-%m-%d"),
                            stop_loss=cost*0.9, target_price=cost*1.2
                        ))
                        st.success("Added")
                        st.rerun()
                    else:
                        st.error("Stock not in universe.")
        with t2:
            if positions:
                with st.form("close_pos_form"):
                    pos_sym = st.selectbox("Ticker", [p["symbol"] for p in positions])
                    exit_px = st.number_input("Exit Price ₹", min_value=1.0)
                    if st.form_submit_button("Close"):
                        pos_to_close = next(p for p in positions if p["symbol"] == pos_sym)
                        PortfolioRepository().close_position(
                            pos_to_close["id"], exit_px,
                            pd.Timestamp.today().strftime("%Y-%m-%d"), "MANUAL"
                        )
                        st.success("Closed")
                        st.rerun()
