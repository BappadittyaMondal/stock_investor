"""
HFOS v5.0 — Calibration & Paper Trading Page
Admin-only: run calibration, approve weights, view paper trade stats.
"""
import streamlit as st
import pandas as pd
from services.auth_service import require_role
from database.db_manager import execute_query


@require_role("ADMIN")
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
    st.title("🔬 Calibration & Paper Trading")
    st.caption("Walk-forward weight optimization • Admin approval required before live use")

    tab1, tab2, tab3 = st.tabs(["📊 Paper Trading", "⚙️ Run Calibration", "📋 Calibration History"])

    # ── Tab 1: Paper Trading ──────────────────────────────────────────────────
    with tab1:
        from engines.paper_trading.paper_trading_engine import PaperTradingEngine
        engine = PaperTradingEngine()

        st.subheader("Performance Stats")
        stats = engine.get_stats()
        if "message" in stats:
            st.info(stats["message"])
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Trades",  stats["total_trades"])
            col2.metric("Win Rate",      f"{stats['win_rate_pct']:.1f}%",
                        delta=f"W:{stats['wins']} L:{stats['losses']} S:{stats['stopped']}")
            col3.metric("Avg P&L",       f"{stats['avg_pnl_pct']:.2f}%")
            col4.metric("Sharpe (est.)", f"{stats['sharpe_est']:.3f}")

            col_a, col_b = st.columns(2)
            col_a.metric("Avg Win",  f"+{stats['avg_win_pct']:.2f}%")
            col_b.metric("Avg Loss", f"{stats['avg_loss_pct']:.2f}%")

        st.divider()
        st.subheader("Close Completed Trades")
        st.caption("Scans all open paper trades against latest prices")
        if st.button("▶ Run Close Evaluation", key="close_paper_btn"):
            with st.spinner("Evaluating open paper trades..."):
                summary = engine.close_trades()
            st.success(
                f"✅ Closed: {summary['closed']} | "
                f"Wins: {summary['wins']} | Losses: {summary['losses']} | "
                f"Stopped: {summary['stopped']} | Still Open: {summary['still_open']}"
            )

        st.divider()
        st.subheader("Open Paper Trades")
        open_trades = engine.get_open_trades()
        if open_trades:
            df = pd.DataFrame(open_trades)
            display = [c for c in ["symbol","sector","alpha_score","signal",
                                    "entry_price","stop_loss","target_price",
                                    "entry_date"] if c in df.columns]
            st.dataframe(df[display].rename(columns={
                "symbol":"Symbol","sector":"Sector","alpha_score":"Alpha",
                "signal":"Signal","entry_price":"Entry ₹","stop_loss":"SL ₹",
                "target_price":"Target ₹","entry_date":"Entry Date"
            }), use_container_width=True, hide_index=True)
        else:
            st.info("No open paper trades. Signals > α75 auto-open paper trades during scans.")

        # Historical closed trades
        closed = execute_query(
            """SELECT pt.*, s.symbol FROM paper_trades pt
               JOIN stocks s ON pt.stock_id=s.id
               WHERE pt.outcome != 'OPEN' ORDER BY pt.exit_date DESC LIMIT 50"""
        )
        if closed:
            st.subheader("Recent Closed Trades")
            df_c = pd.DataFrame([dict(r) for r in closed])
            cols = [c for c in ["symbol","alpha_score","signal","entry_price",
                                  "exit_price","pnl_pct","outcome","entry_date",
                                  "exit_date"] if c in df_c.columns]
            st.dataframe(df_c[cols], use_container_width=True, hide_index=True)

    # ── Tab 2: Run Calibration ────────────────────────────────────────────────
    with tab2:
        st.subheader("Walk-Forward Weight Calibration")
        st.info(
            "This will grid-search optimal alpha engine weights across your paper trade history. "
            "Results save as **DRAFT** and require ADMIN approval before going live."
        )
        st.warning("⚠️ Requires at least 15 closed paper trades for meaningful results.")

        auto_approve = st.checkbox(
            "Auto-approve result (ADMIN only)", value=False, key="auto_approve"
        )
        if st.button("▶ Run Calibration", key="run_cal_btn", type="primary"):
            from engines.calibration.calibration_engine import CalibrationEngine
            from services.auth_service import get_current_user
            user = get_current_user()
            with st.spinner("Running walk-forward calibration (may take 30–60s)..."):
                try:
                    cal = CalibrationEngine()
                    result = cal.run(
                        approved_by=user["user_id"] if auto_approve else None,
                        auto_approve=auto_approve
                    )
                    st.success(f"✅ Calibration complete — Run ID: {result['run_id']}")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Train Sharpe", f"{result['train_sharpe']:.3f}")
                    col2.metric("Test Sharpe",  f"{result['test_sharpe']:.3f}")
                    col3.metric("Max Drawdown", f"{result['max_drawdown']:.2%}")
                    st.subheader("Calibrated Weights")
                    weights = result["weights"]
                    wdf = pd.DataFrame(
                        {"Engine": list(weights.keys()),
                         "Weight": [f"{v:.4f}" for v in weights.values()],
                         "% of Total": [f"{v*100:.1f}%" for v in weights.values()]}
                    )
                    st.dataframe(wdf, use_container_width=True, hide_index=True)
                    st.caption(result["message"])
                except RuntimeError as e:
                    st.error(f"❌ {e}")

    # ── Tab 3: Calibration History ────────────────────────────────────────────
    with tab3:
        st.subheader("Calibration Run History")
        runs = execute_query(
            "SELECT * FROM calibration_runs ORDER BY run_date DESC LIMIT 20"
        )
        if not runs:
            st.info("No calibration runs yet.")
        else:
            df_runs = pd.DataFrame([dict(r) for r in runs])
            st.dataframe(df_runs[[
                "id","run_date","status","sharpe_train","sharpe_test",
                "max_dd_test","positions_tested"
            ]].rename(columns={
                "id":"ID","run_date":"Date","status":"Status",
                "sharpe_train":"Sharpe Train","sharpe_test":"Sharpe Test",
                "max_dd_test":"Max DD","positions_tested":"Trades"
            }), use_container_width=True, hide_index=True)

            # Approve / Reject
            st.divider()
            st.subheader("Approve or Reject a Draft Run")
            draft_ids = [r["id"] for r in runs if r["status"] == "DRAFT"]
            if draft_ids:
                sel_id = st.selectbox("Select Draft Run ID", draft_ids, key="approve_sel")
                col_a, col_b = st.columns(2)
                if col_a.button("✅ Approve", key="approve_btn", type="primary"):
                    from engines.calibration.calibration_engine import CalibrationEngine
                    from services.auth_service import get_current_user
                    user = get_current_user()
                    CalibrationEngine().approve(sel_id, user["user_id"])
                    st.success(f"Run {sel_id} approved — AlphaEngine will use these weights on next restart.")
                    st.rerun()
                if col_b.button("❌ Reject", key="reject_btn"):
                    from engines.calibration.calibration_engine import CalibrationEngine
                    CalibrationEngine().reject(sel_id)
                    st.warning(f"Run {sel_id} rejected.")
                    st.rerun()
            else:
                st.info("No DRAFT runs awaiting approval.")
