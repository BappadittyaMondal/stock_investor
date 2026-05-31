"""HFOS v5.0 — Operations Center"""
import streamlit as st
import pandas as pd
from database.db_manager import execute_query
from monitoring.health_service import HealthService

def render():
    st.title("⚙️ Operations Center")
    st.caption("Self-Monitoring, Observability & Operational Control")

    t_health, t_metrics, t_errors, t_telemetry = st.tabs([
        "🏥 System Health", "📈 Live Metrics", "🚨 Error Dashboard", "⏱️ Telemetry"
    ])

    with t_health:
        st.subheader("Subsystem Health")
        checks = HealthService.run_all_checks()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Database", "🟢 Healthy" if checks["Database"]["status"] == "healthy" else "🔴 Critical")
        c2.metric("Scheduler", "🟢 Healthy" if checks["Scheduler"]["status"] == "healthy" else "🔴 Critical")
        c3.metric("AI Copilot", "🟢 Healthy" if checks["AI Copilot"]["status"] == "healthy" else "🟡 Warning")
        c4.metric("Telegram", "🟢 Healthy" if checks["Telegram"]["status"] == "healthy" else "🔴 Critical")
        
    with t_metrics:
        st.subheader("Live System Metrics")
        metrics = execute_query("SELECT metric_name, metric_value, timestamp FROM system_metrics ORDER BY timestamp DESC LIMIT 50")
        if metrics:
            st.dataframe(pd.DataFrame(metrics), use_container_width=True, hide_index=True)
        else:
            st.info("No metrics recorded yet.")

    with t_errors:
        st.subheader("System Errors")
        errors = execute_query("SELECT timestamp, service_name, severity, error_message, recovery_status FROM system_errors ORDER BY timestamp DESC LIMIT 50")
        if errors:
            st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)
        else:
            st.success("No system errors detected.")

    with t_telemetry:
        st.subheader("Telemetry & Latency")
        logs = execute_query("SELECT timestamp, action_name, result, duration_ms, status FROM telemetry_logs ORDER BY timestamp DESC LIMIT 50")
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
        else:
            st.info("No telemetry logs yet.")
