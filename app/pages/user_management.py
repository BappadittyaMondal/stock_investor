"""HFOS v5.0 — User Management"""
import streamlit as st
import pandas as pd
from database.db_manager import execute_query, execute_write
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
    st.title("👥 User Management")
    st.caption("Manage HFOS access, roles, and status")

    tab1, tab2 = st.tabs(["User List", "Create User"])

    with tab1:
        st.subheader("Existing Users")
        users = execute_query("SELECT id, username, email, role, is_active, last_login, created_at FROM users")
        if users:
            df = pd.DataFrame(users)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("Modify User")
            user_list = [u["username"] for u in users]
            sel_user = st.selectbox("Select User", user_list)
            
            col1, col2 = st.columns(2)
            with col1:
                new_role = st.selectbox("Change Role", ["ADMIN", "ANALYST", "VIEWER", "PORTFOLIO_MANAGER", "RESEARCHER"])
                if st.button("Update Role"):
                    execute_write("UPDATE users SET role=? WHERE username=?", (new_role, sel_user))
                    st.success(f"Role updated to {new_role}")
                    st.rerun()
            with col2:
                current_active = next(u["is_active"] for u in users if u["username"] == sel_user)
                action = "Disable" if current_active else "Enable"
                if st.button(f"{action} User"):
                    new_val = 0 if current_active else 1
                    execute_write("UPDATE users SET is_active=? WHERE username=?", (new_val, sel_user))
                    st.success(f"User {sel_user} is now {'Disabled' if new_val == 0 else 'Enabled'}")
                    st.rerun()

    with tab2:
        st.subheader("Create New User")
        with st.form("create_user_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_pass = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["VIEWER", "ANALYST", "ADMIN"])
            
            if st.form_submit_button("Create User"):
                if not new_username or not new_pass or not new_email:
                    st.error("All fields required")
                else:
                    from services.auth_service import AuthService
                    try:
                        AuthService().register_user(new_username, new_email, new_pass, new_role)
                        st.success(f"User {new_username} created successfully!")
                    except ValueError as e:
                        st.error(str(e))
