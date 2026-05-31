"""HFOS v5.0 — Data Freshness Page"""
import streamlit as st
import pandas as pd
from database.db_manager import execute_query


def render():
    st.title("📈 Data Source Health")

    rows = execute_query("SELECT * FROM data_freshness ORDER BY source")
    if not rows:
        st.info("No freshness data yet. Run a scan to populate.")
        return

    df = pd.DataFrame([dict(r) for r in rows])

    # Status cards
    cols = st.columns(min(len(df), 4))
    for i, row in df.iterrows():
        icon = {"GREEN":"✅","AMBER":"🟡","RED":"🔴"}.get(row["status"],"❓")
        cols[i % 4].metric(
            row["source"],
            f"{icon} {row['status']}",
            f"{row['consecutive_failures']} failures" if row["consecutive_failures"] > 0 else None,
            delta_color="inverse"
        )

    st.divider()
    st.subheader("Detailed Freshness Log")
    st.dataframe(df.rename(columns={
        "source":"Source","last_updated":"Last Updated",
        "status":"Status","consecutive_failures":"Failures","error_message":"Last Error"
    }), use_container_width=True, hide_index=True)

    red = df[df["status"] == "RED"]
    if not red.empty:
        st.error(f"🔴 {len(red)} source(s) are RED — check data pipeline!")
        for _, r in red.iterrows():
            st.write(f"**{r['source']}**: {r.get('error_message','No error message')}")



