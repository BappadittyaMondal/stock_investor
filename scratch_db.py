import sqlite3

db_path = r"database\hfos_production.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Remove old
cur.execute("DELETE FROM stocks WHERE symbol IN ('SMOKE01', 'EXITCO', 'PFCO01')")
cur.execute("DELETE FROM portfolio")
cur.execute("DELETE FROM scores")

real_stocks = [
    ("RELIANCE.NS", "Reliance Industries Ltd", "NSE"),
    ("TCS.NS", "Tata Consultancy Services Ltd", "NSE"),
    ("INFY.NS", "Infosys Ltd", "NSE"),
    ("HDFCBANK.NS", "HDFC Bank Ltd", "NSE"),
    ("ICICIBANK.NS", "ICICI Bank Ltd", "NSE"),
    ("LT.NS", "Larsen & Toubro Ltd", "NSE"),
    ("SBIN.NS", "State Bank of India", "NSE"),
    ("BHARTIARTL.NS", "Bharti Airtel Ltd", "NSE"),
    ("TITAN.NS", "Titan Company Ltd", "NSE"),
    ("ASIANPAINT.NS", "Asian Paints Ltd", "NSE")
]

for s in real_stocks:
    try:
        cur.execute("INSERT INTO stocks (symbol, name, exchange) VALUES (?, ?, ?)", s)
    except sqlite3.IntegrityError:
        pass

conn.commit()
conn.close()
print("Phase 2 Complete")
