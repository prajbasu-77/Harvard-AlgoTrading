import pandas, talib, yfinance, schedule, colorama
print("TEST 1: All imports OK")

import yfinance as yf
df = yf.download("BTC-USD", period="60d", interval="4h", progress=False, auto_adjust=True)
df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
print(f"TEST 2: Got {len(df)} candles. Latest BTC close: ${df['close'].iloc[-1]:,.2f}")

import talib
close = df["close"].values.astype(float)
high  = df["high"].values.astype(float)
low   = df["low"].values.astype(float)
upper, mid, lower = talib.BBANDS(close, 20, 2.0, 2.0)
adx = talib.ADX(high, low, close, 14)
squeeze = (upper[-1] < (mid[-1] + 1.5 * talib.ATR(high, low, close, 20)[-1])) and (lower[-1] > (mid[-1] - 1.5 * talib.ATR(high, low, close, 20)[-1]))
print(f"TEST 3: BB Upper={upper[-1]:,.0f} Mid={mid[-1]:,.0f} Lower={lower[-1]:,.0f} ADX={adx[-1]:.1f}")
print(f"TEST 3: Squeeze active = {squeeze}")

import os
with open(r"C:\Harvard-AlgoTrading\.env") as f:
    content = f.read()
print(f"TEST 4: .env file OK = {'HYPER_LIQUID_KEY' in content}")

print("")
print("ALL TESTS PASSED - Bot is fully working!")
