import os, glob

template = """def render():
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

def _render_body():"""

for f in glob.glob(r'app/pages/*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    if '_render_body' in content:
        continue
    if 'def render():' in content:
        content = content.replace('def render():', template)
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
print("Wrapped all pages.")
