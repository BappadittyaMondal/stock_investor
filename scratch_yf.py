import yfinance as yf
ticker = yf.Ticker("RELIANCE.NS")
info = ticker.info
print(info.get("currentPrice"))
print(info.get("marketCap"))
print(info.get("trailingPE"))
print(info.get("fiftyTwoWeekHigh"))
print(info.get("fiftyTwoWeekLow"))
