"""HFOS v5.0 — Earnings Calendar Page"""
import streamlit as st
import pandas as pd
from database.db_manager import execute_query, execute_write
from repositories.stock_repository import StockRepository


def render():
    st.title("📅 Earnings Calendar")

    tab1, tab2 = st.tabs(["📅 Calendar", "➕ Add Entry"])

    with tab1:
        rows = execute_query(
            """SELECT ec.*, s.symbol, s.name, s.sector
               FROM earnings_calendar ec
               JOIN stocks s ON ec.stock_id=s.id
               ORDER BY ec.earnings_date DESC LIMIT 100"""
        )
        if rows:
            df = pd.DataFrame([dict(r) for r in rows])
            st.dataframe(df[["symbol","name","sector","earnings_date","period",
                              "eps_estimate","eps_actual","surprise_pct"]].rename(columns={
                "symbol":"Symbol","name":"Company","sector":"Sector",
                "earnings_date":"Date","period":"Period",
                "eps_estimate":"EPS Est.","eps_actual":"EPS Actual",
                "surprise_pct":"Surprise %"
            }), use_container_width=True, hide_index=True)
        else:
            st.info("No earnings entries yet. Use the 'Add Entry' tab.")

    with tab2:
        st.subheader("Log Earnings Result")
        srepo = StockRepository()
        with st.form("earnings_form"):
            sym     = st.text_input("Symbol").upper().strip()
            col1,col2 = st.columns(2)
            e_date  = col1.date_input("Earnings Date")
            period  = col2.text_input("Period", placeholder="Q4FY25")
            col3,col4 = st.columns(2)
            eps_est = col3.number_input("EPS Estimate", value=0.0)
            eps_act = col4.number_input("EPS Actual",   value=0.0)
            notes   = st.text_area("Concall Notes")
            if st.form_submit_button("Save Earnings →") and sym:
                stock = srepo.get_by_symbol(sym)
                if not stock:
                    st.error(f"'{sym}' not found.")
                else:
                    surprise = ((eps_act - eps_est) / abs(eps_est) * 100) if eps_est else 0.0
                    execute_write(
                        """INSERT INTO earnings_calendar
                           (stock_id,earnings_date,period,eps_estimate,eps_actual,surprise_pct,concall_notes)
                           VALUES(?,?,?,?,?,?,?)""",
                        (stock["id"], str(e_date), period, eps_est, eps_act, round(surprise,2), notes)
                    )
                    st.success(f"✅ Earnings for {sym} saved. Surprise: {surprise:.1f}%")
                    st.rerun()
