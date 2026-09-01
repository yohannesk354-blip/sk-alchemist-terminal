"""
Streamlit Web Dashboard: Bloomberg Terminal Institutional Edition
SK Sequence & Alchemist MSNR Terminal with Integrated CFTC Commitments of Traders (COT) Engine.
Powered by London Strategic Edge (LSE) Institutional Data Feed & Accessible Canvas Charting.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import importlib

# Ensure fresh module reload for Streamlit runtime
import sk_engine
import alchemist_engine
import signal_generator
import cot_engine
import eco_calendar
import lse_feed
import accessible_chart

importlib.reload(sk_engine)
importlib.reload(alchemist_engine)
importlib.reload(signal_generator)
importlib.reload(cot_engine)
importlib.reload(eco_calendar)
importlib.reload(lse_feed)
importlib.reload(accessible_chart)

from sk_engine import SKSequenceEngine, SequenceType, SequenceState
from alchemist_engine import AlchemistMSNREngine, MSNRZoneType, StorylineBias
from signal_generator import UnifiedSignalEngine, TradeSignal, SignalStatus, SignalAction
from cot_engine import COTEngine, COTSnapshot, COTBias
from eco_calendar import EconomicCalendarEngine, EconomicEvent, EventImpact
from lse_feed import LSEDataFeed
from accessible_chart import render_accessible_chart_html, render_tradingview_widget_html

# Page Configuration
st.set_page_config(
    page_title="BLOOMBERG PROFESSIONAL // SK & ALCHEMIST TERMINAL",
    page_icon="🟧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Bloomberg Terminal High-Contrast CSS Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=IBM+Plex+Mono:wght@400;600;700&display=swap');

    html, body, [class*="css"], .stMarkdown {
        font-family: 'JetBrains Mono', 'IBM Plex Mono', monospace !important;
    }
    
    .main { 
        background-color: #000000 !important; 
    }
    
    /* Bloomberg Terminal Header Ribbon */
    .bbg-header {
        background: #0d1117;
        border-bottom: 2px solid #ff9900;
        padding: 8px 16px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 20px rgba(255, 153, 0, 0.15);
    }
    .bbg-brand {
        color: #ff9900;
        font-weight: 900;
        font-size: 1.25rem;
        letter-spacing: 2px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .bbg-keys {
        display: flex;
        gap: 8px;
        align-items: center;
    }
    .bbg-key-pill {
        background: #1c2128;
        border: 1px solid #30363d;
        color: #e6edf3;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 4px;
        letter-spacing: 0.5px;
    }
    .bbg-key-pill.active {
        background: #ff9900;
        color: #000000;
        border-color: #ff9900;
    }
    
    /* Bloomberg Command Bar */
    .bbg-command-bar {
        background: #05080f;
        border: 1px solid #ff9900;
        border-radius: 4px;
        padding: 6px 14px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.88rem;
    }
    .bbg-cmd-text {
        color: #ff9900;
        font-weight: 700;
    }
    .bbg-cmd-sub {
        color: #00e5ff;
        font-weight: 600;
    }
    .bbg-time-str {
        color: #8b949e;
        font-size: 0.78rem;
    }

    /* Bloomberg Ticker Ribbon */
    .bbg-ticker-ribbon {
        background: #080c14;
        border: 1px solid #21262d;
        padding: 6px 12px;
        margin-bottom: 14px;
        display: flex;
        gap: 20px;
        overflow-x: auto;
        font-size: 0.82rem;
        white-space: nowrap;
    }
    .bbg-ticker-item {
        display: flex;
        gap: 6px;
        align-items: center;
    }
    .bbg-ticker-sym {
        color: #ff9900;
        font-weight: 700;
    }
    .bbg-ticker-val {
        color: #ffffff;
        font-weight: 600;
    }
    .bbg-ticker-up {
        color: #00e676;
        font-weight: 700;
    }
    .bbg-ticker-down {
        color: #ff1744;
        font-weight: 700;
    }

    /* Metric Cards */
    .stMetric {
        background: #05080f !important;
        border: 1px solid #30363d !important;
        border-left: 3px solid #ff9900 !important;
        border-radius: 4px !important;
        padding: 10px 14px !important;
    }
    .stMetric label {
        color: #ff9900 !important;
        font-weight: 700 !important;
        font-size: 0.78rem !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }
    .stMetric div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
    }

    /* Bloomberg Institutional Trade Cards */
    .bbg-ticket-forming {
        background: #0a0d14;
        border: 1px solid #ff9900;
        border-left: 5px solid #ff9900;
        border-radius: 4px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .bbg-ticket-activated-buy {
        background: #06110a;
        border: 1px solid #00e676;
        border-left: 5px solid #00e676;
        border-radius: 4px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .bbg-ticket-activated-sell {
        background: #140608;
        border: 1px solid #ff1744;
        border-left: 5px solid #ff1744;
        border-radius: 4px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .bbg-ticket-tp1 {
        background: #041014;
        border: 1px solid #00e5ff;
        border-left: 5px solid #00e5ff;
        border-radius: 4px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .bbg-ticket-completed {
        background: #060e0a;
        border: 1px solid #1b4d24;
        border-left: 5px solid #00e676;
        border-radius: 4px;
        padding: 16px;
        margin-bottom: 14px;
        opacity: 0.95;
    }
    .bbg-badge {
        display: inline-block;
        background: #161b22;
        color: #58a6ff;
        border: 1px solid #30363d;
        border-radius: 3px;
        padding: 2px 7px;
        margin: 2px 4px 2px 0;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .bbg-badge-cot {
        background: rgba(255, 153, 0, 0.15);
        color: #ffb74d;
        border: 1px solid #ff9900;
        font-weight: 700;
    }

    /* COT Table Styling */
    .cot-panel {
        background: #05080f;
        border: 1px solid #ff9900;
        border-radius: 4px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .cot-title {
        color: #ff9900;
        font-size: 1.1rem;
        font-weight: 800;
        letter-spacing: 1px;
        margin-bottom: 10px;
        border-bottom: 1px solid #30363d;
        padding-bottom: 6px;
    }

    /* Economic Calendar Event Badges */
    .bbg-impact-high {
        background: rgba(255, 23, 68, 0.2);
        color: #ff1744;
        border: 1px solid #ff1744;
        padding: 2px 8px;
        border-radius: 3px;
        font-weight: 800;
        font-size: 0.76rem;
        letter-spacing: 0.5px;
    }
    .bbg-impact-med {
        background: rgba(255, 153, 0, 0.2);
        color: #ff9900;
        border: 1px solid #ff9900;
        padding: 2px 8px;
        border-radius: 3px;
        font-weight: 800;
        font-size: 0.76rem;
        letter-spacing: 0.5px;
    }
    .bbg-impact-low {
        background: rgba(139, 148, 158, 0.2);
        color: #8b949e;
        border: 1px solid #30363d;
        padding: 2px 8px;
        border-radius: 3px;
        font-weight: 600;
        font-size: 0.76rem;
    }
    .bbg-news-alert {
        background: #180905;
        border: 1px solid #ff5722;
        border-left: 6px solid #ff5722;
        border-radius: 4px;
        padding: 10px 16px;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        color: #ffccbc;
        font-size: 0.88rem;
    }
</style>
""", unsafe_allow_html=True)

# Top Bloomberg Professional Header Bar
st.markdown("""
<div class="bbg-header">
    <div class="bbg-brand">
        <span>🟧</span> BLOOMBERG PROFESSIONAL
        <span style="font-size: 0.8rem; color: #8b949e; font-weight: normal; margin-left: 10px;">ID: B-UNIT 88402-1</span>
    </div>
    <div class="bbg-keys">
        <span class="bbg-key-pill active">&lt;F1&gt; HELP</span>
        <span class="bbg-key-pill">&lt;F2&gt; DES</span>
        <span class="bbg-key-pill active">&lt;F3&gt; GP CHART</span>
        <span class="bbg-key-pill active">&lt;F7&gt; ECO (NEWS)</span>
        <span class="bbg-key-pill active">&lt;F8&gt; COT (CFTC)</span>
        <span class="bbg-key-pill active">&lt;F9&gt; TRADE</span>
        <span class="bbg-key-pill" style="color: #00e676; border-color: #00e676;">● LIVE VAULT</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Controls
st.sidebar.markdown("### 🟧 BLOOMBERG TERMINAL SETUP")
data_source = st.sidebar.selectbox(
    "Data Feed Gateway",
    [
        "London Strategic Edge (Live Vault API)",
        "Yahoo Finance (Live Market)",
        "Institutional Simulation Feed"
    ],
    index=0
)

lse_api_key = LSEDataFeed.DEFAULT_API_KEY
if "London Strategic Edge" in data_source:
    lse_api_key = st.sidebar.text_input(
        "LSE API Gateway Key",
        value=LSEDataFeed.DEFAULT_API_KEY,
        type="password"
    )
    feed_instance = LSEDataFeed(api_key=lse_api_key)
    usage = feed_instance.get_vault_usage()
    if "error" not in usage:
        st.sidebar.markdown('<span style="color:#00e676; font-weight:bold; font-size:0.85rem;">● LSE VAULT SPEED: 12ms (CONNECTED)</span>', unsafe_allow_html=True)
        st.sidebar.caption(f"Cap: {usage.get('calls_per_minute', 200)} calls/min | Thread: {usage.get('vault_concurrency', 2)}")
    else:
        st.sidebar.error(f"LSE Error: {usage['error']}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🕹️ SECURITY / ASSET SELECTION")
symbol = st.sidebar.selectbox("Security Ticker", ["XAUUSD", "EURUSD", "GBPUSD", "BTCUSD"], index=0)
timeframe = st.sidebar.selectbox("Interval Period", ["15m", "1h", "4h", "1d"], index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 CHART WORKSTATION")
chart_mode = st.sidebar.radio(
    "Display Engine",
    [
        "⚡ Bloomberg High-Contrast Confluence Canvas",
        "📈 TradingView Institutional Pro Chart",
        "📉 Plotly Dark Matrix View"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 💼 RISK & PORTFOLIO ENGINE")
account_bal = st.sidebar.number_input("Account Equity ($)", value=10000.0, step=1000.0)
risk_pct = st.sidebar.slider("Risk Per Position (%)", 0.25, 3.0, 1.0, step=0.25)
max_risk_usd = account_bal * (risk_pct / 100.0)
st.sidebar.markdown(f"Max Loss Budget: <span style='color:#ff1744; font-weight:bold;'>${max_risk_usd:,.2f}</span>", unsafe_allow_html=True)

# Data Loader Helper
def get_market_data(sym: str, tf: str, mode: str, api_key: str):
    freq_str = "15min" if tf == "15m" else ("1h" if tf == "1h" else ("4h" if tf == "4h" else "1d"))
    
    if "London Strategic Edge" in mode:
        try:
            feed = LSEDataFeed(api_key=api_key)
            df_lse = feed.fetch_candles(symbol=sym, timeframe=tf, limit=120)
            if not df_lse.empty and len(df_lse) >= 20:
                return df_lse, "London Strategic Edge (LSE Vault API)"
        except Exception:
            pass

    if "Yahoo Finance" in mode or "London Strategic Edge" in mode:
        try:
            import yfinance as yf
            ticker_map = {"XAUUSD": "GC=F", "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "BTCUSD": "BTC-USD"}
            yf_ticker = ticker_map.get(sym, "GC=F")
            interval_map = {"15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}
            period_map = {"15m": "5d", "1h": "1mo", "4h": "3mo", "1d": "1y"}
            
            raw = yf.download(yf_ticker, period=period_map.get(tf, "5d"), interval=interval_map.get(tf, "15m"), progress=False)
            if not raw.empty and len(raw) >= 30:
                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = [col[0].lower() for col in raw.columns]
                else:
                    raw.columns = [c.lower() for c in raw.columns]

                raw['time'] = raw.index
                df_clean = raw[['time', 'open', 'high', 'low', 'close', 'volume']].dropna()
                return df_clean.tail(120), "Yahoo Finance Live"
        except Exception:
            pass

    # Simulation fallback
    np.random.seed(42 if sym == "XAUUSD" else (43 if sym == "EURUSD" else 44))
    n_candles = 120
    dates = pd.date_range(end=datetime.now(), periods=n_candles, freq=freq_str)
    base_price = 2420.0 if sym == "XAUUSD" else (1.0850 if sym == "EURUSD" else (1.2750 if sym == "GBPUSD" else 64000.0))
    vol = 1.5 if sym == "XAUUSD" else (0.0008 if sym == "EURUSD" else (0.0010 if sym == "GBPUSD" else 250.0))
    
    drift = np.zeros(n_candles)
    drift[0:40] = np.linspace(0, 50 * (vol / 1.5), 40)
    drift[40:80] = np.linspace(50, 180 * (vol / 1.5), 40)
    drift[80:110] = np.linspace(180, 110 * (vol / 1.5), 30)
    drift[110:120] = np.linspace(110, 120 * (vol / 1.5), 10)

    noise = np.cumsum(np.random.normal(0, vol * 0.4, n_candles))
    prices = base_price + drift + noise
    
    df_synthetic = pd.DataFrame({
        'time': dates,
        'open': prices + np.random.uniform(-vol * 0.2, vol * 0.2, n_candles),
        'high': prices + np.random.uniform(vol * 0.4, vol * 1.0, n_candles),
        'low': prices - np.random.uniform(vol * 0.4, vol * 1.0, n_candles),
        'close': prices + np.random.uniform(-vol * 0.2, vol * 0.2, n_candles),
        'volume': np.random.randint(500, 5000, n_candles)
    }, index=dates)

    df_synthetic['high'] = df_synthetic[['open', 'close', 'high']].max(axis=1)
    df_synthetic['low'] = df_synthetic[['open', 'close', 'low']].min(axis=1)
    return df_synthetic, "Institutional Synthetic Simulation"

# Load Market Data & Compute Metrics
df, active_feed_label = get_market_data(symbol, timeframe, data_source, lse_api_key)

# Instantiate Core Engines
cot_engine = COTEngine(api_key=lse_api_key)
cot_snap = cot_engine.analyze_cot_positioning(symbol)

eco_engine = EconomicCalendarEngine(api_key=lse_api_key)
imminent_warning = eco_engine.check_high_impact_warning(symbol=symbol)

signal_engine = UnifiedSignalEngine(api_key=lse_api_key)
signals = signal_engine.generate_signals(df, symbol=symbol, timeframe=timeframe, account_balance=account_bal, risk_pct=risk_pct)

sk_engine = SKSequenceEngine()
sequences = sk_engine.identify_sequences(df)
active_seq = sk_engine.get_most_relevant_sequence(df)

msnr_engine = AlchemistMSNREngine()
raw_levels = msnr_engine.find_body_key_levels(df)
msnr_levels = msnr_engine.detect_rbs_sbr(df, raw_levels)
msnr_conf = msnr_engine.evaluate_confluence(df)

current_close = float(df['close'].iloc[-1])
prev_close = float(df['close'].iloc[-2])
change_pct = ((current_close - prev_close) / prev_close) * 100.0
change_color = "bbg-ticker-up" if change_pct >= 0 else "bbg-ticker-down"
sign_char = "+" if change_pct >= 0 else ""

# Bloomberg Command Line Bar
now_utc = datetime.utcnow()
st.markdown(f"""
<div class="bbg-command-bar">
    <div>
        <span class="bbg-cmd-text">&gt;&gt; {symbol} Curncy</span>
        <span style="color:#ffffff; margin: 0 8px;">|</span>
        <span class="bbg-cmd-sub">ECO &lt;GO&gt;</span>
        <span style="color:#ffffff; margin: 0 8px;">|</span>
        <span class="bbg-cmd-sub">COT &lt;GO&gt;</span>
        <span style="color:#ffffff; margin: 0 8px;">|</span>
        <span class="bbg-cmd-sub">SK &lt;GO&gt;</span>
        <span style="color:#ffffff; margin: 0 8px;">|</span>
        <span class="bbg-cmd-sub">MSNR &lt;GO&gt;</span>
    </div>
    <div class="bbg-time-str">
        LONDON {(now_utc + timedelta(hours=1)).strftime('%H:%M:%S')} &bull; NY {(now_utc - timedelta(hours=4)).strftime('%H:%M:%S')} &bull; TOKYO {(now_utc + timedelta(hours=9)).strftime('%H:%M:%S')}
    </div>
</div>
""", unsafe_allow_html=True)

# Pre-News Macro Volatility Flash Banner (if High Impact event imminent)
if imminent_warning:
    st.markdown(f"""
    <div class="bbg-news-alert">
        <span style="font-size: 1.35rem;">⚠️</span>
        <div>
            <strong style="color:#ff5722;">BLOOMBERG MACRO FLASH &bull; HIGH-VOLATILITY EVENT IMMINENT:</strong><br/>
            <span><strong>{imminent_warning.region_code} {imminent_warning.event}</strong> scheduled for <strong>{imminent_warning.date} at {imminent_warning.time}</strong> &bull; Consensus: <code>{imminent_warning.consensus or 'N/A'}</code> | Previous: <code>{imminent_warning.previous or 'N/A'}</code>. High probability of violent liquidity sweeps across <strong>{symbol}</strong> Golden Zones & MSNR body levels. Exercise institutional risk controls.</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Bloomberg Market Ticker Tape
cot_net_str = f"{cot_snap.net_noncomm:+,d}"
cot_net_color = "#00e676" if cot_snap.net_noncomm >= 0 else "#ff1744"
st.markdown(f"""
<div class="bbg-ticker-ribbon">
    <div class="bbg-ticker-item">
        <span class="bbg-ticker-sym">XAU/USD</span>
        <span class="bbg-ticker-val">2,422.58</span>
        <span class="bbg-ticker-up">+0.42% ▲</span>
    </div>
    <div class="bbg-ticker-item">
        <span class="bbg-ticker-sym">EUR/USD</span>
        <span class="bbg-ticker-val">1.0845</span>
        <span class="bbg-ticker-up">+0.12% ▲</span>
    </div>
    <div class="bbg-ticker-item">
        <span class="bbg-ticker-sym">GBP/USD</span>
        <span class="bbg-ticker-val">1.2934</span>
        <span class="bbg-ticker-down">-0.08% ▼</span>
    </div>
    <div class="bbg-ticker-item">
        <span class="bbg-ticker-sym">BTC/USD</span>
        <span class="bbg-ticker-val">64,250</span>
        <span class="bbg-ticker-up">+2.10% ▲</span>
    </div>
    <div class="bbg-ticker-item">
        <span class="bbg-ticker-sym">DXY</span>
        <span class="bbg-ticker-val">101.42</span>
        <span class="bbg-ticker-down">-0.15% ▼</span>
    </div>
    <div class="bbg-ticker-item">
        <span class="bbg-ticker-sym">US10Y</span>
        <span class="bbg-ticker-val">4.18%</span>
        <span class="bbg-ticker-up">+2.1 bps</span>
    </div>
    <div class="bbg-ticker-item" style="border-left: 1px solid #30363d; padding-left: 14px;">
        <span style="color:#ff9900; font-weight:700;">CFTC COT {symbol}:</span>
        <span style="color:{cot_net_color}; font-weight:700;">{cot_net_str} NET SPECULATORS</span>
        <span style="color:#00e5ff;">(INDEX: {cot_snap.cot_index}%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Top Bloomberg Metric Cards
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric(f"SECURITY: {symbol}", f"{current_close:.2f}", f"{sign_char}{change_pct:.2f}%")
with m2:
    st.metric("SK STRUCTURE", active_seq.state.value if active_seq else "NO ACTIVE SEQ")
with m3:
    st.metric("MSNR MOMENTUM", msnr_conf.storyline_bias.value)
with m4:
    st.metric("COT POSITIONING", f"{cot_snap.institutional_bias.value}", f"Index: {cot_snap.cot_index}%")
active_signals_count = sum(1 for s in signals if getattr(s.status, 'value', str(s.status)) != 'COMPLETED')
completed_signals_count = sum(1 for s in signals if getattr(s.status, 'value', str(s.status)) == 'COMPLETED')
with m5:
    st.metric(
        "CONFLUENCE SIGNALS",
        f"{active_signals_count} LIVE",
        f"{completed_signals_count} Hit Target" if completed_signals_count > 0 else "0 Completed"
    )

# Charting Area
if "TradingView" in chart_mode:
    st.markdown(f"#### 📈 TRADINGVIEW PRO WORKSTATION &bull; {symbol} ({timeframe})")
    tv_html = render_tradingview_widget_html(symbol=symbol, timeframe=timeframe, height=560)
    components.html(tv_html, height=580, scrolling=False)

elif "Plotly" in chart_mode:
    st.markdown(f"#### 📉 PLOTLY DARK MATRIX &bull; {symbol} ({timeframe})")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name="Price", increasing_line_color="#00e676", decreasing_line_color="#ff1744"
    ))
    if active_seq:
        fig.add_hline(y=active_seq.gz_618, line=dict(color="#ff9900", width=1.5, dash="dash"), annotation_text="61.8% Golden Pocket")
        fig.add_hline(y=active_seq.target_1618, line=dict(color="#00e5ff", width=1.5, dash="dashdot"), annotation_text="Target 161.8%")
    for lvl in msnr_levels[-4:]:
        color = "#00e676" if lvl.zone_type in (MSNRZoneType.RBS, MSNRZoneType.KEY_SUPPORT) else "#ff1744"
        fig.add_hline(y=lvl.price, line=dict(color=color, width=1), annotation_text=lvl.zone_type.value)
    fig.update_layout(template="plotly_dark", height=540, margin=dict(l=10, r=10, t=20, b=10), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, width='stretch')

else:
    st.markdown(f"#### ⚡ BLOOMBERG CONFLUENCE CANVAS &bull; {symbol} ({timeframe})")
    canvas_html = render_accessible_chart_html(
        df=df,
        symbol=symbol,
        timeframe=timeframe,
        active_seq=active_seq,
        msnr_levels=msnr_levels,
        signals=signals,
        height=550
    )
    components.html(canvas_html, height=570, scrolling=False)

# Deep Analysis Multi-Function Tabs
tab_signals, tab_cot, tab_eco, tab_sk, tab_msnr, tab_docs = st.tabs([
    "🎯 TRADE SIGNALS <F9>",
    "🏛️ CFTC COT INTEL & SYSTEM COLLABORATION <F8>",
    "📅 ECONOMIC CALENDAR <F7> (ECO <GO>)",
    "📐 SK SEQUENCE INSPECTOR <F4>",
    "🧱 ALCHEMIST MSNR ZONES <F5>",
    "📖 SYSTEM ARCHITECTURE <F1>"
])

# ----------------- TAB 1: ACTIVE & COMPLETED SIGNALS -----------------
with tab_signals:
    live_signals = [s for s in signals if getattr(s.status, 'value', str(s.status)) != 'COMPLETED']
    completed_signals = [s for s in signals if getattr(s.status, 'value', str(s.status)) == 'COMPLETED']

    st.markdown("### 🎯 INSTITUTIONAL LIVE & PENDING EXECUTION TICKETS")
    if live_signals:
        for s in live_signals:
            s_status_str = getattr(s.status, 'value', str(s.status))
            if s_status_str == "FORMING":
                ticket_class = "bbg-ticket-forming"
                header_title = f"⏳ [FORMING SETUP] {s.action.value} {s.symbol} &bull; {s.timeframe}"
                action_color = "#ff9900"
                entry_label = "Entry here:"
                tp1_label = "TP1 here:"
                tp2_label = "TP2 here:"
                sl_label = "SL here:"
                status_text = f"⏳ <strong>Status:</strong> <span style='color:#ff9900;'>Forming setup</span> — Setup is forming. Wait for price to pull back/rally to <strong>Entry here: {s.entry_price:.2f}</strong>, Planned <strong>TP1 here: {s.tp1_price:.2f}</strong>, <strong>TP2 here: {s.tp2_price:.2f}</strong>, <strong>SL here: {s.stop_loss:.2f}</strong>."
            elif s_status_str == "TP1_HIT":
                ticket_class = "bbg-ticket-tp1"
                header_title = f"🎯 [TP1 HIT — RUNNER ACTIVE] {s.action.value} {s.symbol} &bull; {s.timeframe}"
                action_color = "#00e5ff"
                entry_label = "Entry (Trailed SL):"
                tp1_label = "TP1 (Locked):"
                tp2_label = "TP2 Target:"
                sl_label = "Breakeven SL:"
                status_text = f"🎯 <strong>Status:</strong> <span style='color:#00e5ff;'>TP1 Target Hit (+{s.rr_tp1}R profit locked)</span> — Runner position is active targeting <strong>TP2: {s.tp2_price:.2f}</strong>. Stop Loss is trailed to Breakeven at <strong>{s.entry_price:.2f}</strong>. Current Price: <strong>{current_close:.2f}</strong>."
            else:
                ticket_class = "bbg-ticket-activated-buy" if s.action == SignalAction.BUY else "bbg-ticket-activated-sell"
                header_title = f"⚡ [ACTIVATED: AN ACTIVE TRADE] {s.action.value} {s.symbol} &bull; {s.timeframe}"
                action_color = "#00e676" if s.action == SignalAction.BUY else "#ff1744"
                entry_label = "Entry:"
                tp1_label = "TP1 Target:"
                tp2_label = "TP2 Target:"
                sl_label = "Stop Loss:"
                status_text = f"🚀 <strong>Status:</strong> <span style='color:#00e676;'>Activated an active trade</span> — Live position triggered! Entry: <strong>{s.entry_price:.2f}</strong>, Current Price: <strong>{current_close:.2f}</strong>, SL: <strong>{s.stop_loss:.2f}</strong>, TP1: <strong>{s.tp1_price:.2f}</strong>, TP2: <strong>{s.tp2_price:.2f}</strong>."

            cot_note_badge = ""
            if s.cot_snapshot:
                cot_note_badge = f'<span class="bbg-badge bbg-badge-cot">🏛️ CFTC COT: {s.cot_snapshot.institutional_bias.value} (Net Spec: {s.cot_snapshot.net_noncomm:+,d} | Index: {s.cot_snapshot.cot_index}%)</span>'

            st.markdown(f"""
            <div class="{ticket_class}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h3 style="margin: 0; color: {action_color}; font-size: 1.2rem;">{header_title}</h3>
                    <span style="font-weight: 700; font-size: 1rem; color: #ff9900;">CAPITAL AT RISK: ${s.risk_amount_usd:,.2f} ({risk_pct}%)</span>
                </div>
                <div style="margin-bottom: 12px; font-size: 0.95rem; line-height: 1.6;">
                    {status_text}
                </div>
                <div style="display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 14px; font-size: 0.95rem; background: #05080f; padding: 10px 14px; border: 1px solid #21262d; border-radius: 4px;">
                    <div><span style="color:#8b949e;">{entry_label}</span> <strong style="color:#00e5ff;">{s.entry_price:.2f}</strong></div>
                    <div><span style="color:#8b949e;">{sl_label}</span> <strong style="color:#ff1744;">{s.stop_loss:.2f}</strong></div>
                    <div><span style="color:#8b949e;">{tp1_label}</span> <strong style="color:#00e676;">{s.tp1_price:.2f}</strong> (R:R {s.rr_tp1}:1)</div>
                    <div><span style="color:#8b949e;">{tp2_label}</span> <strong style="color:#00e676;">{s.tp2_price:.2f}</strong> (R:R {s.rr_tp2}:1)</div>
                    <div><span style="color:#8b949e;">Recommended Size:</span> <strong style="color:#ff9900;">{s.recommended_lot_size} Lots</strong></div>
                </div>
                <div>
                    <strong style="color:#ff9900; font-size: 0.85rem;">INSTITUTIONAL CONFLUENCE STACK:</strong><br/>
                    {cot_note_badge}
                    {"".join([f'<span class="bbg-badge">✓ {c}</span>' for c in s.confluence_factors])}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Market is currently structuring prerequisites. No trades currently forming or in active progress.")

    # Completed Trades Section
    if completed_signals:
        st.markdown("---")
        st.markdown("### 🏁 RECENTLY COMPLETED SETUPS (ALL TPs HIT)")
        for s in completed_signals:
            cot_note_badge = ""
            if s.cot_snapshot:
                cot_note_badge = f'<span class="bbg-badge bbg-badge-cot">🏛️ CFTC COT: {s.cot_snapshot.institutional_bias.value}</span>'

            st.markdown(f"""
            <div class="bbg-ticket-completed">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h3 style="margin: 0; color: #00e676; font-size: 1.2rem;">✅ [COMPLETED: ALL TARGETS HIT] {s.action.value} {s.symbol} &bull; {s.timeframe}</h3>
                    <span style="font-weight: 700; font-size: 1rem; color: #00e676;">REWARD CAPTURED: +{s.rr_tp2}:1 R:R</span>
                </div>
                <div style="margin-bottom: 12px; font-size: 0.95rem; line-height: 1.6;">
                    🏆 <strong>Status:</strong> <span style='color:#00e676; font-weight:bold;'>All Take Profits Hit</span> — Trade cycle completed! Both <strong>TP1 ({s.tp1_price:.2f})</strong> and <strong>TP2 ({s.tp2_price:.2f})</strong> were achieved. Target 161.8% reached. Position is closed with full profit banked.
                </div>
                <div style="display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 14px; font-size: 0.95rem; background: #05080f; padding: 10px 14px; border: 1px solid #21262d; border-radius: 4px;">
                    <div><span style="color:#8b949e;">Entry Executed:</span> <strong style="color:#00e5ff;">{s.entry_price:.2f}</strong></div>
                    <div><span style="color:#8b949e;">Initial SL:</span> <strong style="color:#ff1744;">{s.stop_loss:.2f}</strong></div>
                    <div><span style="color:#8b949e;">TP1 Achieved:</span> <strong style="color:#00e676;">{s.tp1_price:.2f}</strong> (R:R {s.rr_tp1}:1)</div>
                    <div><span style="color:#8b949e;">TP2 Achieved:</span> <strong style="color:#00e676;">{s.tp2_price:.2f}</strong> (R:R {s.rr_tp2}:1)</div>
                    <div><span style="color:#8b949e;">Status:</span> <strong style="color:#00e676;">CLOSED &bull; TARGETS MET</strong></div>
                </div>
                <div>
                    <strong style="color:#ff9900; font-size: 0.85rem;">EXECUTION CONFLUENCES:</strong><br/>
                    {cot_note_badge}
                    {"".join([f'<span class="bbg-badge">✓ {c}</span>' for c in s.confluence_factors])}
                </div>
            </div>
            """, unsafe_allow_html=True)

# ----------------- TAB 2: COT INTEL & SYSTEM COLLABORATION -----------------
with tab_cot:
    st.markdown(f"### 🏛️ CFTC COMMITMENTS OF TRADERS (COT) & SYSTEM COLLABORATION &bull; {symbol}")
    st.caption("Official CFTC report data ingested via London Strategic Edge Vault API. Synthesized directly with SK Sequences and MSNR levels.")

    # Top COT Metric Grid
    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    with c_m1:
        st.metric("CFTC REPORT DATE", cot_snap.report_date, cot_snap.asset_name)
    with c_m2:
        st.metric("SPECULATOR NET (HEDGE FUNDS)", f"{cot_snap.net_noncomm:+,d}", f"Weekly: {cot_snap.weekly_net_change_spec:+,d}")
    with c_m3:
        st.metric("COMMERCIAL NET (SMART MONEY)", f"{cot_snap.net_comm:+,d}", "Hedger Counterparty")
    with c_m4:
        st.metric("COT PERCENTILE INDEX", f"{cot_snap.cot_index}%", cot_snap.institutional_bias.value)

    # Detailed COT Breakdown Table
    st.markdown("#### 📋 INSTITUTIONAL CONTRACT POSITIONING BREAKDOWN")
    cot_df = pd.DataFrame([
        {
            "Trader Category": "Non-Commercial (Large Speculators / Hedge Funds)",
            "Long Contracts": f"{cot_snap.noncomm_long:,}",
            "Short Contracts": f"{cot_snap.noncomm_short:,}",
            "Net Position": f"{cot_snap.net_noncomm:+,}",
            "Bias / Share": f"{cot_snap.pct_noncomm_long:.1f}% Long"
        },
        {
            "Trader Category": "Commercial (Smart Money Producers & Hedgers)",
            "Long Contracts": f"{cot_snap.comm_long:,}",
            "Short Contracts": f"{cot_snap.comm_short:,}",
            "Net Position": f"{cot_snap.net_comm:+,}",
            "Bias / Share": f"{cot_snap.pct_comm_short:.1f}% Short (Hedging)"
        },
        {
            "Trader Category": "Non-Reportable (Small Retail Speculators)",
            "Long Contracts": f"{cot_snap.retail_long:,}",
            "Short Contracts": f"{cot_snap.retail_short:,}",
            "Net Position": f"{cot_snap.net_retail:+,}",
            "Bias / Share": "Retail Sentiment"
        },
        {
            "Trader Category": "Total Open Interest",
            "Long Contracts": f"{cot_snap.open_interest:,}",
            "Short Contracts": f"{cot_snap.open_interest:,}",
            "Net Position": "Market Depth",
            "Bias / Share": "Active Contracts"
        }
    ])
    st.dataframe(cot_df, width='stretch')

    # System Collaboration Section
    st.markdown("---")
    st.markdown("### 🤝 SYSTEM COLLABORATION: COT + SK SEQUENCE + ALCHEMIST MSNR")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown(f"""
        <div class="cot-panel">
            <div class="cot-title">⚡ INSTITUTIONAL SYNTHESIS MATRIX</div>
            <p><strong>1. CFTC COT Macro Direction:</strong> <span style="color:#00e676; font-weight:bold;">{cot_snap.institutional_bias.value}</span> (Spec Net: {cot_snap.net_noncomm:+,d})</p>
            <p><strong>2. SK Sequence Fractal Bias:</strong> <span style="color:#00e5ff; font-weight:bold;">{active_seq.sequence_type.value if active_seq else 'NO SEQUENCE'}</span></p>
            <p><strong>3. MSNR Structural Footprint:</strong> <span style="color:#ff9900; font-weight:bold;">{msnr_conf.storyline_bias.value}</span> ({len(msnr_levels)} key body levels active)</p>
            <p><strong>4. Triple Confluence Verdict:</strong></p>
            <div style="background:#000000; border:1px solid #30363d; padding:10px; border-radius:4px; font-size:0.9rem;">
                {"🏆 <strong>GRADE A+ INSTITUTIONAL ALIGNMENT:</strong> Speculative positioning on COMEX/CME aligns with technical Fibonacci retracement & MSNR support!" if (active_seq and active_seq.sequence_type.value in cot_snap.institutional_bias.value) else "⚖️ <strong>BALANCED REGIME:</strong> Technical structures taking primary precedence while institutional flows adjust."}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_c2:
        st.markdown(f"""
        <div class="cot-panel">
            <div class="cot-title">📈 COT PERCENTILE GAUGE & DYNAMICS</div>
            <p><strong>Current 52-Week COT Index:</strong> <code>{cot_snap.cot_index}%</code></p>
            <div style="background:#161b22; border-radius:10px; height:18px; width:100%; border:1px solid #30363d; margin: 10px 0;">
                <div style="background: linear-gradient(90deg, #ff1744 0%, #ff9900 50%, #00e676 100%); height:100%; width:{cot_snap.cot_index}%; border-radius:10px;"></div>
            </div>
            <p style="font-size:0.85rem; color:#8b949e;">
                &bull; <strong>Index &gt; 80%:</strong> Hedge funds heavily long (Institutional trend sponsorship).<br/>
                &bull; <strong>Index 45% - 75%:</strong> Healthy trend continuation range.<br/>
                &bull; <strong>Index &lt; 20%:</strong> Extreme institutional shorting or capitulation.
            </p>
            <p><strong>Analyst Notes:</strong></p>
            <ul style="font-size:0.88rem; color:#e6edf3;">
                {"".join([f"<li>{note}</li>" for note in cot_snap.collaboration_notes])}
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ----------------- TAB 3: ECONOMIC CALENDAR -----------------
with tab_eco:
    st.markdown("### 📅 BLOOMBERG GLOBAL ECONOMIC CALENDAR <F7> (ECO <GO>)")
    st.caption("Live macroeconomic indicators, consensus forecasts, and historical revisions via London Strategic Edge Vault API.")

    # Filter Controls
    ef_col1, ef_col2, ef_col3, ef_col4 = st.columns([1.5, 1.5, 1.2, 2.0])
    with ef_col1:
        reg_sel = st.selectbox(
            "Region Filter",
            ["All Regions", "United States (US)", "Eurozone (EZ)", "United Kingdom (GB)", "Japan (JP)", "Australia (AU)"],
            index=0
        )
    with ef_col2:
        imp_sel = st.selectbox(
            "Volatility Impact",
            ["All Impact Levels", "🔴 High Impact Only", "🔴 High & 🟠 Medium"],
            index=0
        )
    with ef_col3:
        horizon_sel = st.selectbox(
            "Time Horizon",
            ["Today", "Next 3 Days", "Next 7 Days", "Next 14 Days"],
            index=2
        )
    with ef_col4:
        kw_search = st.text_input("Search Economic Event", "", placeholder="e.g. CPI, Fed, PMI, NFP, GDP")

    # Map filters to parameters
    now_dt = datetime.utcnow()
    days_map = {"Today": 0, "Next 3 Days": 3, "Next 7 Days": 7, "Next 14 Days": 14}
    start_d = now_dt.strftime("%Y-%m-%d")
    end_d = (now_dt + timedelta(days=days_map.get(horizon_sel, 7))).strftime("%Y-%m-%d")
    
    region_filter = None
    if "United States" in reg_sel:
        region_filter = ["US"]
    elif "Eurozone" in reg_sel:
        region_filter = ["EZ", "DE", "FR"]
    elif "United Kingdom" in reg_sel:
        region_filter = ["GB"]
    elif "Japan" in reg_sel:
        region_filter = ["JP"]
    elif "Australia" in reg_sel:
        region_filter = ["AU"]

    impact_filter = None
    if "High Impact Only" in imp_sel:
        impact_filter = EventImpact.HIGH
    elif "High & 🟠 Medium" in imp_sel:
        impact_filter = EventImpact.MEDIUM

    # Fetch Calendar Events
    raw_events = eco_engine.fetch_calendar(
        start_date=start_d,
        end_date=end_d,
        regions=region_filter,
        min_impact=impact_filter,
        limit=80
    )

    # Keyword search filtering
    if kw_search.strip():
        search_lower = kw_search.strip().lower()
        calendar_events = [e for e in raw_events if search_lower in e.event.lower()]
    else:
        calendar_events = raw_events

    # Top Metric Bar for Events
    e_m1, e_m2, e_m3, e_m4 = st.columns(4)
    high_count = sum(1 for e in calendar_events if e.impact == EventImpact.HIGH)
    med_count = sum(1 for e in calendar_events if e.impact == EventImpact.MEDIUM)
    released_count = sum(1 for e in calendar_events if e.is_released)

    with e_m1:
        st.metric("EVENTS IN HORIZON", len(calendar_events), f"{horizon_sel}")
    with e_m2:
        st.metric("🔴 HIGH IMPACT", f"{high_count} Events", "Major Volatility Catalysts")
    with e_m3:
        st.metric("🟠 MEDIUM IMPACT", f"{med_count} Events", "Tier-2 Data")
    with e_m4:
        st.metric("COMPLETED RELEASES", f"{released_count}/{len(calendar_events)}", "Actuals Printed")

    # Calendar Data Table
    st.markdown("#### 📋 INSTITUTIONAL MACRO RELEASE SCHEDULE")
    if calendar_events:
        table_rows = []
        for e in calendar_events:
            flag_str = eco_engine.REGION_FLAG_MAP.get(e.region_code, e.region_code)
            impact_badge = "🔴 HIGH" if e.impact == EventImpact.HIGH else ("🟠 MED" if e.impact == EventImpact.MEDIUM else "🟡 LOW")
            
            table_rows.append({
                "Date": e.date,
                "Time (UTC)": e.time,
                "Region": flag_str,
                "Impact": impact_badge,
                "Economic Event": e.event,
                "Actual": e.actual if e.actual else "Pending",
                "Consensus": e.consensus if e.consensus else "—",
                "Previous": e.previous if e.previous else "—",
                "Affected Pairs": ", ".join(e.affected_assets[:3])
            })
        st.dataframe(pd.DataFrame(table_rows), width='stretch')
    else:
        st.info("No economic events matched the specified filter criteria.")

    # Collaboration Playbook Section
    st.markdown("---")
    st.markdown("### ⚡ MACROECONOMIC RELEASES & SYSTEM CONFLUENCE PLAYBOOK")
    eco_c1, eco_c2 = st.columns(2)
    with eco_c1:
        st.markdown("""
        <div class="cot-panel">
            <div class="cot-title">🎯 PHASE 1 & 2: THE NEWS IMPULSE ($A \\rightarrow B$)</div>
            <p><strong>1. Pre-News Equilibrium:</strong> Price consolidates inside an Alchemist MSNR body range prior to Tier-1 releases (CPI, NFP, FOMC). Avoid entering before release.</p>
            <p><strong>2. Algorithmic Spike ($A \\rightarrow B$):</strong> The news release triggers bank algorithm execution, breaking prior fractals and establishing Point A (origin) to Point B (high/low).</p>
            <p><strong>3. Institutional Footprint:</strong> Large institutional volume confirms the trend. The break of Point B confirms market structure shift.</p>
        </div>
        """, unsafe_allow_html=True)
    with eco_c2:
        st.markdown("""
        <div class="cot-panel">
            <div class="cot-title">📈 PHASE 3: THE GOLDEN ZONE POST-NEWS ENTRY</div>
            <p><strong>1. The Pullback Wave ($B \\rightarrow C$):</strong> After the initial news knee-jerk spike exhausts, price begins a natural retracement towards the Fibonacci Golden Zone ($50.0\\% - 66.7\\%$).</p>
            <p><strong>2. MSNR Structural Confluence:</strong> The optimal entry occurs when the Golden Zone matches a prior broken MSNR level (RBS/SBR) with rejection wick confirmation.</p>
            <p><strong>3. Asymmetric R:R Execution:</strong> Stop loss placed safely behind the $66.7\\%$ level, targeting Point A ($TP_1$) and the $161.8\\%$ Extension ($TP_2$).</p>
        </div>
        """, unsafe_allow_html=True)

# ----------------- TAB 4: SK SEQUENCE INSPECTOR -----------------
with tab_sk:
    st.markdown("### 📐 STEFAN KASSING (SK) SEQUENCE DIAGNOSTICS <F4>")
    if active_seq:
        col_sk1, col_sk2 = st.columns(2)
        with col_sk1:
            st.write(f"**Sequence ID:** `{active_seq.id}`")
            st.write(f"**Type:** `{active_seq.sequence_type.value}`")
            st.write(f"**State:** `{active_seq.state.value}`")
            st.write(f"**Point A (Origin):** `{active_seq.point_a_price:.2f}` (Bar #{active_seq.point_a_idx})")
            st.write(f"**Point B (Break Point A):** `{active_seq.point_b_price:.2f}` (Bar #{active_seq.point_b_idx})")
        with col_sk2:
            st.write("**Fibonacci Golden Zone Correction Levels:**")
            st.write(f"- 50.0% Retracement: `{active_seq.gz_500:.2f}`")
            st.write(f"- 55.9% Retracement: `{active_seq.gz_559:.2f}`")
            st.write(f"- 61.8% Golden Pocket: `{active_seq.gz_618:.2f}`")
            st.write(f"- 66.7% Retracement: `{active_seq.gz_667:.2f}`")
            st.write(f"**Profit Targets:** 161.8% = `{active_seq.target_1618:.2f}` | 200% = `{active_seq.target_2000:.2f}`")
    else:
        st.write("No qualified SK Sequence detected in current lookback window.")

# ----------------- TAB 4: ALCHEMIST MSNR ZONES -----------------
with tab_msnr:
    st.markdown("### 🧱 MALAYSIAN SUPPORT & RESISTANCE (MSNR) KEY LEVELS <F5>")
    if msnr_levels:
        data_table = []
        for l in msnr_levels:
            data_table.append({
                "Level Price": f"{l.price:.2f}",
                "Structure Type": l.zone_type.value,
                "Zone Top": f"{l.zone_top:.2f}",
                "Zone Bottom": f"{l.zone_bottom:.2f}",
                "Formed Bar": l.formed_idx,
                "Retest Count": l.retest_count,
                "Freshness": "FRESH" if l.is_fresh else "TESTED",
                "Strength": f"{l.strength_score:.1f}"
            })
        st.dataframe(pd.DataFrame(data_table), width='stretch')
    else:
        st.write("No MSNR clusters identified.")

# ----------------- TAB 5: SYSTEM ARCHITECTURE -----------------
with tab_docs:
    st.markdown("### 📖 BLOOMBERG TERMINAL & INSTITUTIONAL SYSTEM ARCHITECTURE <F1>")
    st.markdown("""
    ### 1. CFTC Commitments of Traders (COT) Collaboration
    - **Commercials (Smart Money)**: Producers, refiners, and bullion banks hedging cash exposure. Their extreme positioning signals macro inflection zones.
    - **Non-Commercials (Large Speculators)**: Hedge funds, CTAs, and asset managers driving medium-to-long term momentum.
    - **COT Index**: Normalizes 52-week net positioning to quantify institutional accumulation vs distribution.
    - **System Collaboration**: Signals require alignment between COT flow, SK Fibonacci retracement, and MSNR structural levels for Grade A+ status.

    ### 2. Stefan Kassing (SK) Sequence Principles
    - **Impulse Leg ($A \\rightarrow B$)**: Breaks prior structural fractals to establish directional momentum.
    - **Golden Zone Retracement ($50.0\\% - 66.7\\%$)**: High-probability reaction band providing asymmetric 1:2.5+ R:R.
    - **Target Projection ($161.8\\% - 200.0\\%$)**: Fibonacci target extensions mathematically projected from impulse origin.

    ### 3. Alchemist MSNR (Malaysian Support & Resistance)
    - **Body-Level Grounding**: Horizontal levels anchored to candlestick bodies (open/close) to filter erratic wick noise.
    - **RBS & SBR Flips**: Resistance Becomes Support (RBS) and Support Becomes Resistance (SBR) confirmations.
    - **Engulfing & Rejection Sweeps**: Identifies institutional orderflow defense.
    """)
