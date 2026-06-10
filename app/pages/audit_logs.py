"""HFOS v5.0 — Audit Log Viewer"""
import streamlit as st
import pandas as pd
from database.db_manager import execute_query
from services.auth_service import require_role

@require_role("ADMIN")
def render():
    try:
        _render_body()
    except Exception as _err:
        import traceback as _tb
        st.error("⚠️ This page encountered an error. Please refresh.")
        with st.expander("🔧 Admin Debug: Error Details"):
            st.code(_tb.format_exc())

def _render_body():
    st.title("🕵️ Audit Log Viewer")
    st.caption("Track system and user activity for security compliance")

    logs = execute_query(
        """SELECT a.id, u.username, a.action, a.resource, a.detail, a.ip_address, a.created_at 
           FROM audit_log a
           LEFT JOIN users u ON a.user_id = u.id
           ORDER BY a.created_at DESC LIMIT 200"""
    )
    if logs:
        df = pd.DataFrame(logs)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No audit logs found.")
