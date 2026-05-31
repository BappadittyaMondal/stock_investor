"""HFOS v5.0 — Macro & Geo-Political Page"""
import streamlit as st
import pandas as pd
from engines.macro.macro_engine import MacroEngine
from engines.geo.geo_engine import GeoEngine
from database.db_manager import execute_query, execute_write


def render():
    st.title("🌐 Macro & Geo-Political Intelligence")

    tab1, tab2 = st.tabs(["📊 Macro Dashboard", "🌍 Geo Events"])

    with tab1:
        macro = MacroEngine()
        score = macro.score()
        st.metric("Macro Score", f"{score:.1f}/100",
                  help="Higher = more favorable macro environment for equities")

        st.subheader("Current Macro Indicators")
        indicators = {
            "RBI Repo Rate (%)":       6.5,
            "CPI Inflation (%)":       4.8,
            "INR/USD":                83.5,
            "GDP Growth (%)":          6.8,
            "PMI Manufacturing":      54.0,
        }
        col1, col2, col3 = st.columns(3)
        for i, (name, val) in enumerate(indicators.items()):
            [col1, col2, col3][i % 3].metric(name, str(val))

        # FII/DII flow
        st.subheader("FII / DII Activity (Last 10 Days)")
        rows = execute_query(
            "SELECT * FROM fii_dii_activity ORDER BY activity_date DESC LIMIT 10"
        )
        if rows:
            df = pd.DataFrame([dict(r) for r in rows])
            st.dataframe(df[["activity_date","fii_net_cr","dii_net_cr"]].rename(columns={
                "activity_date":"Date","fii_net_cr":"FII Net (Cr)","dii_net_cr":"DII Net (Cr)"
            }), use_container_width=True, hide_index=True)
        else:
            st.info("No FII/DII data yet.")

        # Log FII data
        with st.expander("Log FII/DII Data"):
            with st.form("fii_form"):
                col_a,col_b,col_c = st.columns(3)
                act_date = col_a.date_input("Date")
                fii_net  = col_b.number_input("FII Net (Cr)", value=0.0, step=100.0)
                dii_net  = col_c.number_input("DII Net (Cr)", value=0.0, step=100.0)
                if st.form_submit_button("Save FII/DII"):
                    execute_write(
                        "INSERT OR REPLACE INTO fii_dii_activity(activity_date,fii_net_cr,dii_net_cr) VALUES(?,?,?)",
                        (str(act_date), fii_net, dii_net)
                    )
                    st.success("Saved FII/DII data")
                    st.rerun()

    with tab2:
        geo = GeoEngine()
        geo_score = geo.score()
        st.metric("Geo-Political Score", f"{geo_score:.1f}/100",
                  help="Higher = calmer geopolitical environment")

        # Recent events
        events = execute_query(
            "SELECT * FROM geo_events ORDER BY event_date DESC LIMIT 20"
        )
        if events:
            df = pd.DataFrame([dict(r) for r in events])
            st.dataframe(df[["event_date","event_type","title","severity","affected_sectors"]].rename(columns={
                "event_date":"Date","event_type":"Type","title":"Event",
                "severity":"Severity","affected_sectors":"Affected Sectors"
            }), use_container_width=True, hide_index=True)

        # Log event
        st.subheader("Log Geo Event")
        with st.form("geo_form"):
            col1,col2 = st.columns(2)
            etype    = col1.selectbox("Event Type", [
                "BORDER_TENSION","TRADE_WAR","SANCTIONS","OIL_SHOCK",
                "CURRENCY_CRISIS","ELECTION","RBI_POLICY","SEBI_REGULATION","OTHER"
            ])
            severity = col2.selectbox("Severity", ["LOW","MEDIUM","HIGH","CRITICAL"])
            title    = st.text_input("Title")
            summary  = st.text_area("Summary", height=80)
            sectors  = st.text_input("Affected Sectors (comma-separated)")
            source   = st.text_input("Source URL (optional)")
            if st.form_submit_button("Log Event →") and title:
                geo.log_event(etype, title, severity, summary, sectors, source)
                st.success(f"✅ Geo event logged: {title}")
                st.rerun()
