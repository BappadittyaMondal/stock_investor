"""HFOS v5.0 — Institutional Data Center"""
import streamlit as st
import pandas as pd
from database.db_manager import execute_query

def render():
    st.title("🗄️ Data Center")
    st.caption("Institutional Data Quality & Reliability Operations")
    
    tab1, tab2, tab3 = st.tabs(["📊 Data Source Health", "🚨 Anomalies", "📈 Quality Metrics"])
    
    with tab1:
        st.subheader("Data Sources")
        health_data = execute_query("SELECT * FROM data_source_health")
        if health_data:
            df_health = pd.DataFrame(health_data)
            st.dataframe(df_health, use_container_width=True, hide_index=True)
        else:
            st.info("No data sources registered in health monitor.")
            
        st.subheader("Feed Freshness (Legacy Monitor)")
        fresh_data = execute_query("SELECT * FROM data_freshness")
        if fresh_data:
            st.dataframe(pd.DataFrame(fresh_data), use_container_width=True, hide_index=True)
            
    with tab2:
        st.subheader("Data Anomalies")
        anomalies = execute_query("""
            SELECT d.detected_at, s.symbol, d.anomaly_type, d.description, d.resolved
            FROM data_anomalies d 
            LEFT JOIN stocks s ON d.stock_id = s.id
            ORDER BY d.detected_at DESC LIMIT 50
        """)
        if anomalies:
            df_anomalies = pd.DataFrame(anomalies)
            st.dataframe(df_anomalies, use_container_width=True, hide_index=True)
        else:
            st.success("No active anomalies detected.")
            
    with tab3:
        st.subheader("Data Quality Scores")
        metrics = execute_query("SELECT source, quality_score, completeness, freshness, consistency, accuracy, reliability, evaluated_at FROM data_quality_metrics ORDER BY evaluated_at DESC LIMIT 20")
        if metrics:
            df_metrics = pd.DataFrame(metrics)
            st.dataframe(df_metrics, use_container_width=True, hide_index=True)
        else:
            st.info("No quality metrics generated yet.")
