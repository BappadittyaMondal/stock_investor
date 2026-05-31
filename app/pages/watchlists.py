"""HFOS v5.0 — Watchlists Page
Tabbed card-based UI.
"""
import streamlit as st
from repositories.watchlist_repository import WatchlistRepository
from repositories.stock_repository import StockRepository

TIER_LABELS = {
    "HIGH_CONVICTION":    ("🚀", "High Conviction", "#00ff88"),
    "EMERGING_LEADERS":   ("⭐", "Emerging Leaders", "#4ade80"),
    "POLICY_BENEFICIARIES":("🏛", "Policy Beneficiaries", "#60a5fa"),
    "TURNAROUND":         ("🔄", "Turnarounds", "#fbbf24"),
    "SPECULATIVE":        ("⚡", "Special Situations", "#f87171"),
}

def render():
    st.title("📋 Watchlists")
    st.caption("Active monitoring for immediate execution.")
    
    repo = WatchlistRepository()
    srepo = StockRepository()
    all_lists = repo.get_all()
    
    # ── Tabs ───────────────────────────────────────────────────────────────
    tabs = st.tabs([f"{emoji} {label}" for _, (emoji, label, _) in TIER_LABELS.items()])
    
    for i, (tier_key, (emoji, label, color)) in enumerate(TIER_LABELS.items()):
        with tabs[i]:
            items = all_lists.get(tier_key, [])
            if not items:
                st.info(f"No stocks in {label}.")
            else:
                # Build Card-based UI
                for item in items:
                    sym = item["symbol"]
                    sector = item.get("sector", "Unknown")
                    cap = item.get("market_cap_cr", 0)
                    added = item.get("added_at", "").split(" ")[0]
                    notes = item.get("notes", "") or "No notes provided."
                    
                    st.markdown(f"""
                    <div style="background: #1a2035; border: 1px solid #2d3f6e; border-left: 5px solid {color}; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="margin: 0; color: #e2e8f0;">{sym}</h3>
                            <span style="background: #0f1629; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; color: #94a3b8;">{sector}</span>
                        </div>
                        <p style="margin: 5px 0 10px 0; color: #94a3b8; font-size: 0.9rem;">{notes}</p>
                        <div style="display: flex; gap: 15px; font-size: 0.8rem; color: #64748b;">
                            <span>Mkt Cap: ₹{cap:,.0f} Cr</span>
                            <span>Added: {added}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Remove {sym}", key=f"rm_{tier_key}_{sym}", type="tertiary"):
                        stock = srepo.get_by_symbol(sym)
                        if stock:
                            repo.remove(stock["id"], tier_key)
                            st.rerun()

    st.divider()

    # Add to watchlist
    with st.expander("➕ Add Stock"):
        with st.form("add_wl_form"):
            c1, c2 = st.columns(2)
            sym = c1.text_input("Ticker").upper()
            tier = c2.selectbox("List", list(TIER_LABELS.keys()), format_func=lambda t: TIER_LABELS[t][1])
            notes = st.text_input("Notes")
            if st.form_submit_button("Add"):
                stock = srepo.get_by_symbol(sym)
                if stock:
                    repo.add(tier, stock["id"], tier, notes=notes)
                    st.success("Added")
                    st.rerun()
                else:
                    st.error("Stock not in database.")
