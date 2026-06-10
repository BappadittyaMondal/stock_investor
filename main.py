"""
HFOS v5.0 — Main Streamlit Application
Hedge-Fund Operating System | Indian Equity Markets
Run: streamlit run main.py
"""
import os
import sys
import streamlit as st
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Boot sequence
# ---------------------------------------------------------------------------
def _boot():
    from core.logging_setup import setup_logging
    setup_logging()
    from database.db_manager import initialize_schema
    initialize_schema()
    from config.settings import validate_critical_settings
    warnings = validate_critical_settings()
    # Store warnings in session state — display only AFTER login to avoid
    # leaking internal configuration state to unauthenticated users.
    if "boot_warnings" not in st.session_state:
        st.session_state["boot_warnings"] = warnings or []
    from jobs.scheduler import start_scheduler
    if "scheduler_started" not in st.session_state:
        start_scheduler()
        st.session_state["scheduler_started"] = True



# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="HFOS v5.0 | Hedge-Fund Operating System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

_boot()

# ---------------------------------------------------------------------------
# CSS — Dark premium theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background: #0a0e1a; color: #e2e8f0; }
    .stSidebar { background: #0f1629 !important; border-right: 1px solid #1e2d4a; }
    .metric-card {
        background: linear-gradient(135deg, #1a2035 0%, #0f1629 100%);
        border: 1px solid #2d3f6e; border-radius: 12px;
        padding: 1rem; margin: 0.25rem 0;
    }
    .signal-STRONG_BUY { color: #00ff88; font-weight: 700; }
    .signal-BUY        { color: #4ade80; font-weight: 600; }
    .signal-ACCUMULATE { color: #fbbf24; font-weight: 500; }
    .signal-WATCH      { color: #94a3b8; }
    .signal-REJECT     { color: #f87171; }
    .alpha-high { color: #00ff88; }
    .alpha-mid  { color: #fbbf24; }
    .alpha-low  { color: #f87171; }
    .disclaimer {
        background: #1a1a2e; border: 1px solid #3d2b1f;
        border-radius: 8px; padding: 0.5rem 1rem;
        font-size: 0.75rem; color: #94a3b8; margin-top: 1rem;
    }
    h1, h2, h3 { color: #e2e8f0 !important; }
    .stButton>button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: white; border: none; border-radius: 8px;
        font-weight: 600; transition: all 0.2s;
    }
    .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37,99,235,0.4); }
</style>
<link rel="manifest" href="/manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/service_worker.js')
        .then(function(registration) {
            console.log('ServiceWorker registration successful with scope: ', registration.scope);
        })
        .catch(function(err) {
            console.log('ServiceWorker registration failed: ', err);
        });
    }
</script>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Auth check
# ---------------------------------------------------------------------------
def _auth_page():
    st.title("🔐 HFOS Login")
    st.markdown("**Hedge-Fund Operating System v5.0**")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            submitted = st.form_submit_button("Login →", use_container_width=True)
            if submitted:
                from services.auth_service import AuthService
                try:
                    svc   = AuthService()
                    token = svc.login(username, password)
                    st.session_state["hfos_token"]    = token
                    st.session_state["hfos_username"] = username
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ {e}")
        st.markdown("""<div class="disclaimer">
            ⚠️ Not SEBI Registered | Private Research Only | Not Investment Advice
        </div>""", unsafe_allow_html=True)

from services.auth_service import get_current_user
user = get_current_user()
if not user and os.environ.get("HFOS_JWT_SECRET"):
    _auth_page()
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 📈 HFOS v5.0")
if user:
    st.sidebar.markdown(f"👤 **{st.session_state.get('hfos_username','User')}** | `{user.get('role','VIEWER')}`")
    if st.sidebar.button("Logout", key="logout_btn"):
        from services.auth_service import AuthService
        AuthService().logout(st.session_state.get("hfos_token",""), user["user_id"])
        for k in ["hfos_token","hfos_username"]:
            st.session_state.pop(k, None)
        st.rerun()
    # Show boot warnings only to authenticated users (ADMIN only)
    if user.get("role") == "ADMIN":
        for w in st.session_state.get("boot_warnings", []):
            st.sidebar.warning(f"⚠️ {w}")

st.sidebar.divider()

# Build nav — calibration only shown to ADMIN / PORTFOLIO_MANAGER
_role = user.get("role", "VIEWER") if user else "VIEWER"

# ── Workspace ──
st.sidebar.caption("📊 WORKSPACE")
WORKSPACE_PAGES = {
    "🏠 Dashboard":         "dashboard",
    "🔍 Universe Scanner":  "scanner",
    "📊 Portfolio":         "portfolio",
    "📋 Watchlists":        "watchlists",
}
# ── Research ──
st.sidebar.caption("🔬 RESEARCH")
RESEARCH_PAGES = {
    "📰 News & Sentiment":  "news",
    "💡 AI Copilot":        "ai_copilot",
    "📅 Earnings Calendar": "earnings",
    "🌐 Macro & Geo":       "macro",
    "🧪 Research Lab":      "research_lab",
    "🧭 Screener Builder":   "screener_builder",
    "👔 Executive Summary": "executive",
    "📱 Mobile App":        "mobile",
}
# ── System (admin) ──
st.sidebar.caption("⚙️ SYSTEM")
SYSTEM_PAGES = {
    "⚙️ Settings":          "settings",
    "📈 Data Freshness":    "freshness",
    "🗄️ Data Center":       "data_center",
    "⚙️ Operations Center": "operations_center",
}
if _role in ("ADMIN", "PORTFOLIO_MANAGER"):
    SYSTEM_PAGES["🔬 Calibration"] = "calibration"
if _role == "ADMIN":
    SYSTEM_PAGES["👥 User Management"] = "user_management"
    SYSTEM_PAGES["🕵️ Audit Logs"] = "audit_logs"

PAGES = {**WORKSPACE_PAGES, **RESEARCH_PAGES, **SYSTEM_PAGES}
page = st.sidebar.radio("Navigate", list(PAGES.keys()), key="nav")
page_id = PAGES[page]
st.sidebar.divider()
st.sidebar.markdown("""<div class="disclaimer">
⚠️ Not SEBI Registered<br>Private Research Only<br>Not Investment Advice
</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Page Routing
# ---------------------------------------------------------------------------
if page_id == "dashboard":
    from app.pages.dashboard import render
    render()
elif page_id == "scanner":
    from app.pages.scanner import render
    render()
elif page_id == "portfolio":
    from app.pages.portfolio import render
    render()
elif page_id == "watchlists":
    from app.pages.watchlists import render
    render()
elif page_id == "news":
    from app.pages.news_page import render
    render()
elif page_id == "ai_copilot":
    from app.pages.ai_copilot_page import render
    render()
elif page_id == "earnings":
    from app.pages.earnings import render
    render()
elif page_id == "macro":
    from app.pages.macro_geo import render
    render()
elif page_id == "settings":
    from app.pages.settings import render
    render()
elif page_id == "freshness":
    from app.pages.freshness import render
    render()
elif page_id == "calibration":
    from app.pages.calibration import render
    render()
elif page_id == "data_center":
    from app.pages.data_center import render
    render()
elif page_id == "operations_center":
    from app.pages.operations_center import render
    render()
elif page_id == "research_lab":
    from app.pages.research_lab import render
    render()
elif page_id == "screener_builder":
    from app.pages.screener_builder import render
    render()
elif page_id == "mobile":
    from app.pages.mobile_dashboard import render
    render()
elif page_id == "executive":
    from app.pages.executive_dashboard import render
    render()
elif page_id == "user_management":
    from app.pages.user_management import render
    render()
elif page_id == "audit_logs":
    from app.pages.audit_logs import render
    render()
