"""
Original Streamlit Web Dashboard
Enhanced with Accessible Financial Charting and London Strategic Edge Data Feed.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
from datetime import datetime

from sk_engine import SKSequenceEngine, SequenceType
from alchemist_engine import AlchemistMSNREngine
from signal_generator import UnifiedSignalEngine
from cot_engine import COTEngine
from eco_calendar import EconomicCalendarEngine, EventImpact
from lse_feed import LSEDataFeed
from accessible_chart import render_accessible_chart_html, render_tradingview_widget_html

st.set_page_config(page_title="BLOOMBERG // SK & Alchemist Terminal", layout="wide")
st.title("⚡ SK Sequence, MSNR & CFTC COT Institutional Terminal")

symbol = st.sidebar.selectbox("Asset Pair", ["XAUUSD", "EURUSD", "GBPUSD", "BTCUSD"])
timeframe = st.sidebar.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=0)
account_bal = st.sidebar.number_input("Account Balance ($)", value=10000.0)
risk_pct = st.sidebar.slider("Risk Per Trade (%)", 0.5, 3.0, 1.0)

feed_choice = st.sidebar.selectbox("Data Feed", ["London Strategic Edge (Live Vault)", "Synthetic Simulation"])
lse_api_key = st.sidebar.text_input("LSE API Key", value=LSEDataFeed.DEFAULT_API_KEY, type="password")

chart_choice = st.sidebar.radio("Chart Type", ["⚡ Accessible Confluence Canvas", "📈 TradingView Pro Widget"], index=0)

# Ingest live London Strategic Edge market data or fallback to simulation
df = None
if feed_choice == "London Strategic Edge (Live Vault)":
    try:
        feed = LSEDataFeed(api_key=lse_api_key)
        df = feed.fetch_candles(symbol=symbol, timeframe=timeframe, limit=120)
        st.sidebar.success("Connected to London Strategic Edge Vault API")
    except Exception as e:
        st.sidebar.warning(f"LSE Feed notice: {e}. Falling back to simulation.")

if df is None:
    tf_map = {"15m": "15min", "1h": "1h", "4h": "4h", "1d": "1D"}
    freq_str = tf_map.get(timeframe, "15min")
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=120, freq=freq_str)
    prices = 2420.0 + np.cumsum(np.random.normal(0.2, 1.5, 120))
    df = pd.DataFrame({
        'time': dates,
        'open': prices + np.random.uniform(-0.5, 0.5, 120),
        'high': prices + np.random.uniform(0.8, 2.0, 120),
        'low': prices - np.random.uniform(0.8, 2.0, 120),
        'close': prices + np.random.uniform(-0.5, 0.5, 120),
        'volume': np.random.randint(500, 5000, 120)
    }, index=dates)

signal_engine = UnifiedSignalEngine()
signals = signal_engine.generate_signals(df, symbol=symbol, timeframe=timeframe, account_balance=account_bal, risk_pct=risk_pct)

sk_engine = SKSequenceEngine()
active_seq = sk_engine.get_most_relevant_sequence(df)

msnr_engine = AlchemistMSNREngine()
raw_levels = msnr_engine.find_body_key_levels(df)
msnr_levels = msnr_engine.detect_rbs_sbr(df, raw_levels)

# Render Chart
if "TradingView" in chart_choice:
    tv_html = render_tradingview_widget_html(symbol=symbol, timeframe=timeframe, height=550)
    components.html(tv_html, height=570, scrolling=False)
else:
    chart_html = render_accessible_chart_html(
        df=df,
        symbol=symbol,
        timeframe=timeframe,
        active_seq=active_seq,
        msnr_levels=msnr_levels,
        signals=signals,
        height=550
    )
    components.html(chart_html, height=570, scrolling=False)

cot_engine = COTEngine(api_key=lse_api_key)
cot_snap = cot_engine.analyze_cot_positioning(symbol)

# COT Institutional Summary Ribbon
st.info(f"🏛️ **CFTC COT Report ({cot_snap.report_date}) &bull; {symbol}:** Speculator Net: **{cot_snap.net_noncomm:+,d} contracts** | Commercial Net: **{cot_snap.net_comm:+,d}** | 52-Wk COT Index: **{cot_snap.cot_index}%** ({cot_snap.institutional_bias.value})")

# Economic Calendar Ribbon
eco_engine = EconomicCalendarEngine(api_key=lse_api_key)
imminent_warning = eco_engine.check_high_impact_warning(symbol=symbol)
if imminent_warning:
    st.warning(f"⚠️ **BLOOMBERG MACRO FLASH:** High-impact event scheduled: **{imminent_warning.region_code} {imminent_warning.event}** on **{imminent_warning.date} at {imminent_warning.time}** (Consensus: {imminent_warning.consensus or 'N/A'}). Expect volatility spikes across {symbol}.")

# Signals Display
st.subheader("🎯 Active Trade Signals")
if signals:
    for s in signals:
        if s.status.value == "FORMING":
            st.warning(f"**[FORMING SETUP] {s.action.value} {s.symbol}** | Entry here: {s.entry_price:.2f} | TP1 here: {s.tp1_price:.2f} (R:R {s.rr_tp1}:1) | TP2 here: {s.tp2_price:.2f} (R:R {s.rr_tp2}:1) | SL here: {s.stop_loss:.2f} | Size: {s.recommended_lot_size} Lots")
            st.write(f"⏳ **Status:** **Forming** — Setup is forming. Entry here: `{s.entry_price:.2f}`, TP1 here: `{s.tp1_price:.2f}`, TP2 here: `{s.tp2_price:.2f}`, SL here: `{s.stop_loss:.2f}`")
            st.write("**Confluences:** " + " | ".join(s.confluence_factors))
        elif s.status.value == "TP1_HIT":
            st.info(f"**[TP1 HIT — RUNNER ACTIVE] {s.action.value} {s.symbol}** | Entry (Trailed SL): {s.entry_price:.2f} | TP1 (Locked): {s.tp1_price:.2f} (+{s.rr_tp1}R) | TP2 Target: {s.tp2_price:.2f} (R:R {s.rr_tp2}:1)")
            st.write(f"🎯 **Status:** **TP1 Target Hit (+{s.rr_tp1}R)** — Runner active towards TP2 (`{s.tp2_price:.2f}`). SL moved to Breakeven (`{s.entry_price:.2f}`).")
            st.write("**Confluences:** " + " | ".join(s.confluence_factors))
        elif s.status.value == "COMPLETED":
            st.success(f"**[COMPLETED: ALL TARGETS HIT] {s.action.value} {s.symbol}** | Entry: {s.entry_price:.2f} | TP1: {s.tp1_price:.2f} | TP2: {s.tp2_price:.2f} (+{s.rr_tp2}:1 R:R Banked)")
            st.write(f"🏆 **Status:** **All Take Profits Hit** — Trade completed! Both TP1 and TP2 were hit for full profit. Position closed.")
            st.write("**Confluences:** " + " | ".join(s.confluence_factors))
        else: # ACTIVATED
            st.success(f"**[ACTIVATED: AN ACTIVE TRADE] {s.action.value} {s.symbol}** | Entry: {s.entry_price:.2f} | SL: {s.stop_loss:.2f} | TP1: {s.tp1_price:.2f} (R:R {s.rr_tp1}:1) | TP2: {s.tp2_price:.2f} (R:R {s.rr_tp2}:1) | Size: {s.recommended_lot_size} Lots")
            st.write(f"🚀 **Status:** **Activated an active trade** — Position is live! Entry: `{s.entry_price:.2f}`, SL: `{s.stop_loss:.2f}`, TP1: `{s.tp1_price:.2f}`, TP2: `{s.tp2_price:.2f}`")
            st.write("**Confluences:** " + " | ".join(s.confluence_factors))
else:
    st.info("Market is currently structuring prerequisites. No trade active.")
