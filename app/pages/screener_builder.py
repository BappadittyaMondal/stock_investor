"""
HFOS v5.0 - Screener Builder
Simple visual builder for the universal screener engine.
"""
import json

import streamlit as st
import pandas as pd

from engines.screener.universal_screener import UniversalScreener


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
    st.title("Screener Builder")
    st.caption("Build nested stock screens on top of the institutional screener engine.")

    engine = UniversalScreener()
    templates = engine.list_templates()

    category_names = [c.get("name", "Category") for c in templates.get("categories", [])]
    category = st.selectbox("Template category", category_names or ["None"])

    selected_template = None
    for c in templates.get("categories", []):
        if c.get("name") == category:
            template_names = [t.get("name", "Template") for t in c.get("templates", [])]
            template_name = st.selectbox("Template", template_names or ["None"], key="template_name")
            for t in c.get("templates", []):
                if t.get("name") == template_name:
                    selected_template = t
                    break
            break

    if selected_template:
        st.subheader("Filter definition")
        st.json(selected_template["filters"])
        if st.button("Run template", use_container_width=True):
            results = engine.run(selected_template["filters"], limit=250)
            if not results:
                st.warning("No matches returned for this template.")
            else:
                df = pd.DataFrame(results)
                st.dataframe(df[["symbol", "name", "score"]], use_container_width=True, hide_index=True)

    st.subheader("Custom filter JSON")
    draft = st.text_area(
        "Edit the filter tree",
        value=json.dumps(selected_template["filters"] if selected_template else {"all": []}, indent=2),
        height=320,
    )

    if st.button("Run custom filter", use_container_width=True):
        try:
            definition = json.loads(draft)
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
            return
        results = engine.run(definition, limit=250)
        if not results:
            st.warning("No matches returned for this filter.")
        else:
            df = pd.DataFrame(results)
            st.dataframe(df[["symbol", "name", "score"]], use_container_width=True, hide_index=True)

