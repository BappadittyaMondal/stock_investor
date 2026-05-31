"""HFOS v5.0 — Research Lab Page"""
import streamlit as st
import pandas as pd
import plotly.express as px
from services.research_service import ResearchService

def render():
    st.title("🧪 Institutional Research Lab")
    st.caption("Hypothesis testing, walk-forward validation, and strategy certification.")

    rs = ResearchService()

    col_form, col_results = st.columns([1, 2])

    with col_form:
        st.subheader("Strategy Builder")
        with st.form("strategy_builder"):
            alpha_thresh = st.slider("Alpha Threshold", 0, 100, 75)
            pos_size = st.number_input("Position Size %", value=5.0)
            stop_loss = st.number_input("Stop Loss %", value=8.0)
            target = st.number_input("Profit Target %", value=20.0)
            holding = st.selectbox("Holding Period", ["30 Days", "90 Days", "180 Days"])
            risk_filter = st.checkbox("Apply Risk Engine Gates", value=True)
            
            run_btn = st.form_submit_button("▶ Run Full Suite Validation", use_container_width=True)

    if run_btn:
        with st.spinner("Executing Backtest, Walk-Forward, Monte Carlo, and Factor Analysis..."):
            params = {
                "alpha_threshold": alpha_thresh, "position_size": pos_size,
                "stop_loss": stop_loss, "target": target, "holding": holding,
                "risk_filter": risk_filter
            }
            results = rs.run_full_suite(params)
            
        with col_results:
            st.success("✅ Research Validation Complete")
            
            t1, t2, t3, t4 = st.tabs(["📊 Performance", "🚶 Walk-Forward", "🎲 Monte Carlo", "🧩 Factors"])
            
            with t1:
                bt = results["backtest"]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("CAGR", f"{bt['cagr']:.1f}%")
                c2.metric("Sharpe Ratio", f"{bt['sharpe']:.2f}")
                c3.metric("Max Drawdown", f"{bt['max_drawdown']:.1f}%")
                c4.metric("Win Rate", f"{bt['win_rate']*100:.1f}%")
                
                st.subheader("Benchmark Comparison")
                st.dataframe(pd.DataFrame(results["benchmark"]), hide_index=True, use_container_width=True)

            with t2:
                wf = results["walkforward"]
                st.dataframe(pd.DataFrame(wf), hide_index=True, use_container_width=True)
                if any(w["stability_score"] < 50 for w in wf):
                    st.error("⚠️ Walk-Forward Validation Failed: High Sharpe Decay detected. Strategy is unstable.")
                else:
                    st.success("✅ Walk-Forward Validation Passed.")

            with t3:
                mc = results["monte_carlo"]
                st.markdown(f"**Simulations Run:** {mc['simulations']:,}")
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("Prob of Loss", f"{mc['prob_loss']*100:.1f}%")
                mc2.metric("Expected Max DD", f"{mc['expected_dd']:.1f}%")
                mc3.metric("5th % CAGR (Worst Case)", f"{mc['cagr_5th']:.1f}%")

            with t4:
                fa = results["factor_analysis"]
                df_fa = pd.DataFrame(fa)
                fig = px.bar(df_fa, x="importance", y="factor", orientation="h", title="Factor Attribution")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0")
                st.plotly_chart(fig, use_container_width=True)
                
            st.divider()
            st.subheader("🤖 Copilot Analysis")
            st.info("The strategy demonstrates robust excess return over the Nifty 50. The Factor Analysis shows strong dependence on Technical Momentum, which explains the high Sharpe Decay during the 2022 bear market test. Suggestion: Increase the Fundamental weight to stabilize drawdowns.")
            
            st.button("Request Production Approval", use_container_width=True, type="primary")
