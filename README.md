# ⚡ SK Sequence & Alchemist MSNR Institutional Terminal

A quantitative trading terminal combining **Stefan Kassing (SK) Fibonacci Sequence Theory** with **Alchemist Malaysian Support and Resistance (MSNR)** price action frameworks.

---

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
