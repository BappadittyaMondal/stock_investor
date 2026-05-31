"""
HFOS v5.0 — Settings Page
Manage configurations and Stock Universe uploads.
"""
import streamlit as st
import pandas as pd
from config.settings import (
    DB_PATH, ANTHROPIC_MODEL, AI_DAILY_LIMIT_INR,
    AI_MONTHLY_LIMIT_INR, MAX_PORTFOLIO_POSITIONS,
    CAPITAL_INR, MAX_POSITION_SIZE_PCT
)
from repositories.stock_repository import StockRepository


def render():
    st.title("⚙️ Settings")
    st.info("Settings are managed via environment variables. Edit your `.env` file to change values.")

    st.subheader("Current Configuration")
    config = {
        "DB_PATH":                  DB_PATH,
        "ANTHROPIC_MODEL":          ANTHROPIC_MODEL,
        "AI_DAILY_LIMIT_INR":       f"₹{AI_DAILY_LIMIT_INR}",
        "AI_MONTHLY_LIMIT_INR":     f"₹{AI_MONTHLY_LIMIT_INR}",
        "MAX_PORTFOLIO_POSITIONS":  MAX_PORTFOLIO_POSITIONS,
        "CAPITAL_INR":              f"₹{CAPITAL_INR:,.0f}",
        "MAX_POSITION_SIZE_PCT":    f"{MAX_POSITION_SIZE_PCT}%",
    }
    for k, v in config.items():
        col1, col2 = st.columns([2, 3])
        col1.code(k)
        col2.write(str(v))

    st.divider()
    st.subheader("Stock Universe Management")
    st.write("Upload a CSV of stocks (columns: symbol, name, exchange, sector, market_cap_cr)")
    uploaded = st.file_uploader("Upload stocks.csv", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        required = {"symbol", "name"}
        if not required.issubset(set(df.columns)):
            st.error(f"CSV must have columns: {required}")
        else:
            count = StockRepository().bulk_upsert(df.to_dict("records"))
            st.success(f"✅ Upserted {count} stocks into universe")
