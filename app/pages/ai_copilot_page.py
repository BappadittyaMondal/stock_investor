"""HFOS v5.0 — AI Copilot Page
One-click prompt decision assistant.
"""
import streamlit as st
from services.ai_copilot import AICopilot
from services.portfolio_service import PortfolioService

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
    st.title("💡 AI Copilot")
    st.caption("Context-aware decision assistant.")

    ai = AICopilot()
    spend = ai.get_monthly_spend()
    from config.settings import AI_MONTHLY_LIMIT_INR
    
    st.markdown(f"<div style='text-align: right; font-size: 0.8rem; color: #94a3b8;'>Cost this month: ₹{spend:.2f} / ₹{AI_MONTHLY_LIMIT_INR:.0f}</div>", unsafe_allow_html=True)
    if spend >= AI_MONTHLY_LIMIT_INR:
        st.error("⛔ Monthly AI budget exhausted.")
        return

    # One-click quick prompts
    st.subheader("⚡ Quick Insights")
    c1, c2, c3, c4 = st.columns(4)
    
    # Session state for prompt handling
    if "copilot_prompt" not in st.session_state:
        st.session_state.copilot_prompt = ""
        
    def set_prompt(text):
        st.session_state.copilot_prompt = text
        
    with c1:
        st.button("🔍 Best stocks under current risk regime", on_click=set_prompt, args=("What are the best stocks under the current risk regime based on recent alpha scores?",), use_container_width=True)
    with c2:
        st.button("💼 Comprehensive portfolio review", on_click=set_prompt, args=("Run a comprehensive portfolio review.",), use_container_width=True)
    with c3:
        st.button("📉 Why did Alpha fall today?", on_click=set_prompt, args=("Explain the common factors causing alpha scores to fall in the current market breadth.",), use_container_width=True)
    with c4:
        st.button("❓ Explain a specific signal", on_click=set_prompt, args=("Explain what a 'STRONG_BUY' signal means and what constraints are checked before entry.",), use_container_width=True)

    st.divider()

    # Chat interface
    st.subheader("Chat")
    prompt = st.chat_input("Ask Copilot (e.g. 'Summarize TCS concall')")
    
    # Initialize thread
    from services.auth_service import get_current_user
    from database.db_manager import execute_query, execute_write, execute_one
    
    user = get_current_user()
    user_id = user["user_id"] if user else 0
    
    # Simple single-thread approach for the current user
    thread = execute_one("SELECT id FROM ai_threads WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,))
    if not thread:
        execute_write("INSERT INTO ai_threads(user_id, title) VALUES(?,?)", (user_id, "Main Thread"))
        thread = execute_one("SELECT id FROM ai_threads WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,))
    
    thread_id = thread["id"]
    
    # Load history
    msgs = execute_query("SELECT role, content FROM ai_messages WHERE thread_id=? ORDER BY created_at ASC", (thread_id,))
    for m in msgs:
        st.chat_message(m["role"]).write(m["content"])
        
    # Use session state prompt if quick button was clicked, or chat input
    active_prompt = prompt or st.session_state.copilot_prompt
    
    if active_prompt:
        execute_write("INSERT INTO ai_messages(thread_id, role, content) VALUES(?,?,?)", (thread_id, 'user', active_prompt))
        st.chat_message("user").write(active_prompt)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                if "portfolio review" in active_prompt.lower():
                    ps = PortfolioService()
                    positions = ps.get_active_positions()
                    if not positions:
                        res = "No active positions to review."
                    else:
                        pf_text = "\n".join(f"- {p['symbol']}: qty={p['quantity']}, avg=₹{p['avg_cost']}" for p in positions)
                        res = ai.portfolio_review(pf_text)
                else:
                    # Provide previous context
                    context = "\n".join([f"{m['role']}: {m['content']}" for m in msgs[-5:]])
                    res = ai.ask(active_prompt, context)
                st.write(res)
                execute_write("INSERT INTO ai_messages(thread_id, role, content) VALUES(?,?,?)", (thread_id, 'assistant', res))
        
        # Clear the session state prompt after processing
        st.session_state.copilot_prompt = ""
