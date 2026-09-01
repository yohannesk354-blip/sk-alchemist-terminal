# ⚡ SK Sequence & Alchemist MSNR Institutional Terminal
[![Deploy to Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=yohannesk354-blip/sk-alchemist-terminal&branch=main&mainModule=app.py)

A quantitative Bloomberg-style trading terminal combining **Stefan Kassing (SK) Fibonacci Sequence Theory**, **Alchemist Malaysian Support and Resistance (MSNR)** price action frameworks, **CFTC Commitments of Traders (COT)** institutional data, and **Economic News Calendar (ECO <GO>)**.

---

## 🌐 100% Free Cloud Hosting (No Credit Card Required)

This application can be deployed for **$0.00 / free forever** using **Streamlit Community Cloud** connected directly to GitHub:

1. Push this repository to your GitHub account.
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and log in with your GitHub account.
3. Click **"New app"**, select your repository, set the main file path to `app.py`, and click **"Deploy!"**.
4. Your terminal will be live on the web with a custom URL (e.g. `https://your-terminal.streamlit.app`).

## 🏛️ System Architecture

1. **Stefan Kassing (SK) Sequence Engine (`sk_engine.py`)**:
   - Automated identification of impulse waves ($A \rightarrow B$).
   - Determination of **Break Point A**.
   - Mechanical calculation of the **Golden Zone** (50.0%, 55.9%, 61.8%, 66.7% retracements).
   - Invalidation tracking and extension targets (**161.8%** and **200.0%**).

2. **Alchemist MSNR Engine (`alchemist_engine.py`)**:
   - Candlestick body key level clustering (open/close boundaries).
   - Resistance-Becomes-Support (**RBS**) and Support-Becomes-Resistance (**SBR**) flip classification.
   - Institutional **Bullish/Bearish Engulfing** confirmation detection.
   - **Liquidity sweep** and rejection wick tracking.
   - Higher-timeframe **Storyline bias** calculation.

3. **Unified Signal Engine (`signal_generator.py`)**:
   - Confluence matrix matching SK Golden Zone pullbacks with MSNR RBS/SBR levels.
   - Dynamic stop-loss and dual take-profit calculation ($TP_1$ at Break Point A / 1:3 R:R, $TP_2$ at 161.8% extension).
   - Institutional position sizing (lot sizing) respecting account equity and risk percentage across Gold, FX, and Crypto.

4. **Web Terminal (`app.py` / `dashboard_original.py`)**:
   - Interactive Plotly dark candlestick chart with shaded Golden Zones and MSNR lines.
   - Live real-time market data via Yahoo Finance (`GC=F`, `EURUSD=X`, `GBPUSD=X`, `BTC-USD`) with synthetic scenario fallback.
   - Risk management calculator, sequence inspector, and level breakdown.

---

## 🚀 Quickstart

### 1. Activate Environment
```bash
cd /Users/nova/.gemini/antigravity-ide/scratch/sk-alchemist-terminal
source .venv/bin/activate
```

### 2. Run the Terminal
```bash
streamlit run app.py
```
Or run the original dashboard snippet:
```bash
streamlit run dashboard_original.py
```

### 3. Run Automated Tests
```bash
pytest -v test_terminal.py
```
