"""
Moon Dev BB Squeeze ADX - Paper Trading Bot
Data source: yfinance (BTC-USD)
"""

import sys, os, time, schedule
import pandas as pd
import numpy as np
import traceback
import talib
from termcolor import colored
import colorama
from colorama import Fore
from datetime import datetime
import yfinance as yf

colorama.init(autoreset=True)

PAPER_TRADE       = False
SYMBOL            = 'BTC-USD'
LEVERAGE          = 5
POSITION_SIZE_USD = 10.0
BB_WINDOW         = 20
BB_STD            = 2.0
KELTNER_WINDOW    = 20
KELTNER_ATR_MULT  = 1.5
ADX_PERIOD        = 14
ADX_THRESHOLD     = 25
TAKE_PROFIT_PCT   = 5.0
STOP_LOSS_PCT     = -3.0

paper_balance  = 100.0
paper_position = None
paper_trades   = []

def paper_status():
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}  PAPER TRADE ACCOUNT STATUS")
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.GREEN}  Balance     : ${paper_balance:.2f}")
    if paper_position:
        price = get_price()
        if price:
            pnl = ((price - paper_position['entry']) / paper_position['entry']) * 100
            if not paper_position['is_long']: pnl *= -1
            pnl *= LEVERAGE
            usd = paper_position['size_usd'] * pnl / 100
            c = Fore.GREEN if usd >= 0 else Fore.RED
            print(f"{Fore.YELLOW}  Position    : {'LONG' if paper_position['is_long'] else 'SHORT'} BTC")
            print(f"{Fore.YELLOW}  Entry       : ${paper_position['entry']:,.2f}")
            print(f"{Fore.YELLOW}  Current     : ${price:,.2f}")
            print(f"{c}  PnL         : {pnl:.2f}% (${usd:.2f})")
    else:
        print(f"{Fore.BLUE}  Position    : None")
    print(f"{Fore.CYAN}  Trades Done : {len(paper_trades)}")
    if paper_trades:
        wins = sum(1 for t in paper_trades if t['pnl'] > 0)
        total = len(paper_trades)
        total_pnl = sum(t['pnl'] for t in paper_trades)
        c = Fore.GREEN if total_pnl >= 0 else Fore.RED
        print(f"{Fore.CYAN}  Win Rate    : {wins}/{total} ({wins/total*100:.1f}%)")
        print(f"{c}  Total PnL   : ${total_pnl:.2f}")
    print(f"{Fore.CYAN}{'='*60}\n")

def get_price():
    try:
        t = yf.Ticker('BTC-USD')
        df = t.history(period='1d', interval='1m')
        return float(df['Close'].iloc[-1])
    except:
        return None

def get_ohlcv():
    try:
        df = yf.download('BTC-USD', period='60d', interval='4h', progress=False, auto_adjust=True)
        df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
        df = df[['open','high','low','close','volume']].dropna()
        return df
    except Exception as e:
        print(f"{Fore.RED}  Data error: {e}")
        return None

def calc_indicators(df):
    try:
        close = df['close'].values.astype(float)
        high  = df['high'].values.astype(float)
        low   = df['low'].values.astype(float)
        df['upper_bb'], df['middle_bb'], df['lower_bb'] = talib.BBANDS(close, BB_WINDOW, BB_STD, BB_STD)
        df['atr']    = talib.ATR(high, low, close, KELTNER_WINDOW)
        df['kc_mid'] = talib.SMA(close, KELTNER_WINDOW)
        df['upper_kc'] = df['kc_mid'] + KELTNER_ATR_MULT * df['atr']
        df['lower_kc'] = df['kc_mid'] - KELTNER_ATR_MULT * df['atr']
        df['adx']    = talib.ADX(high, low, close, ADX_PERIOD)
        df['squeeze'] = (df['upper_bb'] < df['upper_kc']) & (df['lower_bb'] > df['lower_kc'])
        return df
    except Exception as e:
        print(f"{Fore.RED}  Indicator error: {e}")
        return None

def enter(is_long, price):
    global paper_position
    if paper_position: return
    paper_position = {'is_long': is_long, 'entry': price, 'size_usd': POSITION_SIZE_USD}
    side = 'LONG' if is_long else 'SHORT'
    c = Fore.GREEN if is_long else Fore.RED
    print(f"\n{c}  >>> PAPER {side} @ ${price:,.2f} | Size ${POSITION_SIZE_USD} x{LEVERAGE}")

def exit_pos(price, reason):
    global paper_position, paper_balance
    if not paper_position: return
    pnl = ((price - paper_position['entry']) / paper_position['entry']) * 100
    if not paper_position['is_long']: pnl *= -1
    pnl *= LEVERAGE
    usd = paper_position['size_usd'] * pnl / 100
    paper_balance += usd
    c = Fore.GREEN if usd >= 0 else Fore.RED
    print(f"\n{c}  >>> EXIT @ ${price:,.2f} | {reason} | PnL: {pnl:.2f}% (${usd:.2f})")
    paper_trades.append({'pnl': usd, 'pct': pnl, 'reason': reason})
    paper_position = None

def check_tp_sl():
    if not paper_position: return
    price = get_price()
    if not price: return
    pnl = ((price - paper_position['entry']) / paper_position['entry']) * 100
    if not paper_position['is_long']: pnl *= -1
    pnl *= LEVERAGE
    if pnl >= TAKE_PROFIT_PCT:
        exit_pos(price, f'TAKE PROFIT +{TAKE_PROFIT_PCT}%')
    elif pnl <= STOP_LOSS_PCT:
        exit_pos(price, f'STOP LOSS {STOP_LOSS_PCT}%')

def bot():
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}  BB SQUEEZE BOT | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.CYAN}  Mode: PAPER TRADING")
    print(f"{Fore.CYAN}{'='*60}")

    if paper_position:
        check_tp_sl()
        paper_status()
        return

    df = get_ohlcv()
    if df is None or len(df) < 25:
        print(f"{Fore.RED}  Not enough data ({len(df) if df is not None else 0} candles)")
        return

    df = calc_indicators(df)
    if df is None: return

    cur  = df.iloc[-1]
    prev = df.iloc[-2]
    price = get_price() or float(cur['close'])

    print(f"{Fore.GREEN}  BTC Price : ${price:,.2f}")
    print(f"{Fore.GREEN}  ADX       : {cur['adx']:.2f}  (need > {ADX_THRESHOLD})")
    squeeze_txt = 'YES - waiting for breakout...' if cur['squeeze'] else 'NO'
    print(f"{Fore.YELLOW}  Squeeze   : {squeeze_txt}")

    squeeze_released = bool(prev['squeeze']) and not bool(cur['squeeze'])

    if squeeze_released and cur['adx'] > ADX_THRESHOLD:
        print(f"\n{Fore.MAGENTA}  *** SQUEEZE RELEASED + STRONG TREND! ***")
        if float(cur['close']) > float(cur['upper_bb']):
            print(f"{Fore.GREEN}  Signal: LONG breakout!")
            enter(True, price)
        elif float(cur['close']) < float(cur['lower_bb']):
            print(f"{Fore.RED}  Signal: SHORT breakdown!")
            enter(False, price)
        else:
            print(f"{Fore.YELLOW}  Squeeze released but no clear direction yet.")
    else:
        print(f"{Fore.BLUE}  No signal. Monitoring...")

    paper_status()

def main():
    print(f"{Fore.CYAN}\n{'='*60}")
    print(f"{Fore.YELLOW}  Moon Dev BB Squeeze ADX - PAPER TRADING BOT")
    print(f"{Fore.CYAN}  Symbol  : BTC-USD (via yfinance)")
    print(f"{Fore.CYAN}  Balance : ${paper_balance:.2f} virtual")
    print(f"{Fore.CYAN}  Leverage: {LEVERAGE}x  |  TP: +{TAKE_PROFIT_PCT}%  |  SL: {STOP_LOSS_PCT}%")
    print(f"{Fore.CYAN}{'='*60}\n")

    bot()
    schedule.every(1).minutes.do(bot)
    print(f"{Fore.GREEN}  Running every 1 min. Press Ctrl+C to stop.\n")

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}  Bot stopped by user.")
            paper_status()
            break
        except Exception as e:
            print(f"{Fore.RED}  Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
