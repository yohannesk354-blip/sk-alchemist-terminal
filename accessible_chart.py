"""
Accessible Interactive Institutional Financial Charting Component
High-performance, self-contained SVG/HTML5 candlestick chart engine.
Zero external CDN dependencies. Fully accessible with ARIA standards,
crosshair telemetry, SK Golden Zones, Alchemist MSNR levels, and trade brackets.
"""
import json
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np

from sk_engine import SKSequence
from alchemist_engine import MSNRLevel, MSNRZoneType
from signal_generator import TradeSignal


def render_accessible_chart_html(
    df: pd.DataFrame,
    symbol: str = "XAUUSD",
    timeframe: str = "15m",
    active_seq: Optional[SKSequence] = None,
    msnr_levels: Optional[List[MSNRLevel]] = None,
    signals: Optional[List[TradeSignal]] = None,
    height: int = 560
) -> str:
    """
    Generates a fully self-contained HTML/JS/SVG interactive candlestick chart.
    Ensures 100% offline accessibility, fast rendering, and zero CDN failure points.
    """
    if df.empty:
        return "<div style='color:#ef4444;padding:20px;'>No market data available to render chart.</div>"

    # Prepare candle data JSON
    candles_data = []
    for idx, row in df.iterrows():
        t_str = str(row['time']) if 'time' in row else str(idx)
        # Format cleanly
        if len(t_str) > 19:
            t_str = t_str[:19]
        candles_data.append({
            "t": t_str,
            "o": round(float(row['open']), 4),
            "h": round(float(row['high']), 4),
            "l": round(float(row['low']), 4),
            "c": round(float(row['close']), 4),
            "v": round(float(row['volume']), 1) if 'volume' in row else 0.0
        })

    # Prepare SK Golden Zone and targets
    sk_data = {}
    if active_seq:
        sk_data = {
            "type": active_seq.sequence_type.value,
            "state": active_seq.state.value,
            "gz_500": round(active_seq.gz_500, 4),
            "gz_559": round(active_seq.gz_559, 4),
            "gz_618": round(active_seq.gz_618, 4),
            "gz_667": round(active_seq.gz_667, 4),
            "target_1618": round(active_seq.target_1618, 4),
            "target_2000": round(active_seq.target_2000, 4),
            "break_point_a": round(active_seq.break_point_a, 4),
            "start_idx": min(active_seq.point_b_idx, len(candles_data) - 1)
        }

    # Prepare MSNR levels
    levels_data = []
    if msnr_levels:
        for lvl in msnr_levels[-6:]:
            levels_data.append({
                "price": round(lvl.price, 4),
                "type": lvl.zone_type.value,
                "fresh": lvl.is_fresh
            })

    # Prepare Active Trade Signal (Prioritize live active/forming over completed)
    signal_data = {}
    if signals:
        live_sigs = [s for s in signals if getattr(s, 'status', None) != 'COMPLETED' and str(getattr(s, 'status', '')).upper() not in ('COMPLETED', 'SIGNALSTATUS.COMPLETED')]
        sig = live_sigs[0] if live_sigs else signals[0]
        status_val = sig.status.value if hasattr(sig.status, 'value') else str(sig.status)
        signal_data = {
            "action": sig.action.value if hasattr(sig.action, 'value') else str(sig.action),
            "status": status_val,
            "entry": round(sig.entry_price, 4),
            "sl": round(sig.stop_loss, 4),
            "tp1": round(sig.tp1_price, 4),
            "tp2": round(sig.tp2_price, 4),
            "rr_tp1": sig.rr_tp1,
            "rr_tp2": sig.rr_tp2,
            "lots": sig.recommended_lot_size,
            "desc": sig.status_description if hasattr(sig, 'status_description') else ""
        }

    candles_json = json.dumps(candles_data)
    sk_json = json.dumps(sk_data)
    levels_json = json.dumps(levels_data)
    signal_json = json.dumps(signal_data)

    latest_close = candles_data[-1]['c']
    first_close = candles_data[0]['c']
    change_pct = round(((latest_close - first_close) / first_close) * 100, 2)
    change_color = "#10b981" if change_pct >= 0 else "#ef4444"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background-color: #0b0f19;
                color: #e5e7eb;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                overflow: hidden;
                user-select: none;
            }}
            #chart-wrapper {{
                position: relative;
                width: 100%;
                height: {height}px;
                background: #0b0f19;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                display: flex;
                flex-direction: column;
            }}
            #chart-header {{
                height: 42px;
                background: rgba(255, 255, 255, 0.02);
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 16px;
                font-size: 13px;
            }}
            .header-info {{
                display: flex;
                align-items: center;
                gap: 16px;
            }}
            .asset-tag {{
                font-weight: 700;
                font-size: 14px;
                color: #f3f4f6;
                letter-spacing: 0.5px;
            }}
            .tf-tag {{
                background: rgba(59, 130, 246, 0.2);
                color: #60a5fa;
                border: 1px solid rgba(59, 130, 246, 0.4);
                padding: 2px 6px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
            }}
            .ohlc-display {{
                display: flex;
                gap: 12px;
                color: #9ca3af;
                font-family: monospace;
                font-size: 12px;
            }}
            .ohlc-display span strong {{
                color: #e5e7eb;
            }}
            #canvas-container {{
                position: relative;
                flex: 1;
                width: 100%;
                height: calc(100% - 42px);
            }}
            canvas {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                cursor: crosshair;
            }}
            .legend-badge {{
                display: inline-flex;
                align-items: center;
                gap: 5px;
                font-size: 11px;
                color: #d1d5db;
            }}
            .badge-dot {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
            }}
            /* High Contrast Accessibility Focus */
            #chart-wrapper:focus-visible {{
                outline: 2px solid #3b82f6;
            }}
        </style>
    </head>
    <body>
        <div id="chart-wrapper" tabindex="0" role="region" aria-label="Interactive Candlestick Chart for {symbol} {timeframe}">
            <div id="chart-header">
                <div class="header-info">
                    <span class="asset-tag">{symbol}</span>
                    <span class="tf-tag">{timeframe}</span>
                    <div class="ohlc-display" id="ohlc-val">
                        <span>O: <strong id="val-o">-</strong></span>
                        <span>H: <strong id="val-h">-</strong></span>
                        <span>L: <strong id="val-l">-</strong></span>
                        <span>C: <strong id="val-c">-</strong></span>
                        <span>Vol: <strong id="val-v">-</strong></span>
                    </div>
                </div>
                <div style="display: flex; gap: 14px; align-items: center;">
                    <div class="legend-badge">
                        <span class="badge-dot" style="background: #f59e0b;"></span>
                        <span>SK Golden Zone (50%-66.7%)</span>
                    </div>
                    <div class="legend-badge">
                        <span class="badge-dot" style="background: #10b981;"></span>
                        <span>MSNR RBS Support</span>
                    </div>
                    <div class="legend-badge">
                        <span class="badge-dot" style="background: #ef4444;"></span>
                        <span>MSNR SBR Resist</span>
                    </div>
                </div>
            </div>
            <div id="canvas-container">
                <canvas id="mainCanvas"></canvas>
            </div>
        </div>

        <script>
            (function() {{
                const candles = {candles_json};
                const sk = {sk_json};
                const levels = {levels_json};
                const signal = {signal_json};

                const container = document.getElementById('canvas-container');
                const canvas = document.getElementById('mainCanvas');
                const ctx = canvas.getContext('2d');

                const valO = document.getElementById('val-o');
                const valH = document.getElementById('val-h');
                const valL = document.getElementById('val-l');
                const valC = document.getElementById('val-c');
                const valV = document.getElementById('val-v');

                let width = container.clientWidth;
                let height = container.clientHeight;
                let hoverIndex = -1;

                function resize() {{
                    const dpr = window.devicePixelRatio || 1;
                    width = container.clientWidth;
                    height = container.clientHeight;
                    canvas.width = width * dpr;
                    canvas.height = height * dpr;
                    canvas.style.width = width + 'px';
                    canvas.style.height = height + 'px';
                    ctx.scale(dpr, dpr);
                    draw();
                }}

                function draw() {{
                    ctx.clearRect(0, 0, width, height);

                    if (!candles || candles.length === 0) return;

                    const paddingRight = 75;
                    const paddingBottom = 26;
                    const chartWidth = width - paddingRight;
                    const chartHeight = height - paddingBottom;
                    const volumeHeight = chartHeight * 0.18;
                    const priceChartHeight = chartHeight - volumeHeight;

                    // Calculate price min & max
                    let minPrice = Infinity;
                    let maxPrice = -Infinity;
                    let maxVol = 0;

                    for (let i = 0; i < candles.length; i++) {{
                        if (candles[i].l < minPrice) minPrice = candles[i].l;
                        if (candles[i].h > maxPrice) maxPrice = candles[i].h;
                        if (candles[i].v > maxVol) maxVol = candles[i].v;
                    }}

                    // Include SK Golden Zone and signals in bounds
                    if (sk && sk.gz_667) {{
                        minPrice = Math.min(minPrice, sk.gz_667 * 0.998);
                        maxPrice = Math.max(maxPrice, sk.gz_500 * 1.002);
                        if (sk.target_1618) {{
                            minPrice = Math.min(minPrice, sk.target_1618 * 0.998);
                            maxPrice = Math.max(maxPrice, sk.target_1618 * 1.002);
                        }}
                    }}
                    if (signal && signal.entry) {{
                        minPrice = Math.min(minPrice, signal.sl * 0.999);
                        maxPrice = Math.max(maxPrice, signal.tp1 * 1.001);
                    }}

                    const priceRange = maxPrice - minPrice || 1;
                    minPrice -= priceRange * 0.05;
                    maxPrice += priceRange * 0.05;
                    const totalRange = maxPrice - minPrice;

                    function getY(p) {{
                        return priceChartHeight - ((p - minPrice) / totalRange) * priceChartHeight;
                    }}

                    function getX(i) {{
                        return (i + 0.5) * (chartWidth / candles.length);
                    }}

                    const candleW = Math.max(2, (chartWidth / candles.length) * 0.75);

                    // Grid Lines
                    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
                    ctx.lineWidth = 1;
                    const gridSteps = 6;
                    for (let s = 0; s <= gridSteps; s++) {{
                        const y = (priceChartHeight / gridSteps) * s;
                        ctx.beginPath();
                        ctx.moveTo(0, y);
                        ctx.lineTo(chartWidth, y);
                        ctx.stroke();

                        // Price label on right axis
                        const pVal = maxPrice - (s / gridSteps) * totalRange;
                        ctx.fillStyle = '#6b7280';
                        ctx.font = '10px monospace';
                        ctx.textAlign = 'left';
                        ctx.fillText(pVal.toFixed(2), chartWidth + 8, y + 3);
                    }}

                    // Render SK Golden Zone Band (50% to 66.7%)
                    if (sk && sk.gz_500 && sk.gz_667) {{
                        const yGzTop = getY(Math.max(sk.gz_500, sk.gz_667));
                        const yGzBot = getY(Math.min(sk.gz_500, sk.gz_667));
                        const xStart = getX(sk.start_idx || 0);

                        ctx.fillStyle = 'rgba(245, 158, 11, 0.15)';
                        ctx.fillRect(xStart, yGzTop, chartWidth - xStart, yGzBot - yGzTop);

                        ctx.strokeStyle = 'rgba(245, 158, 11, 0.5)';
                        ctx.setLineDash([3, 3]);
                        ctx.strokeRect(xStart, yGzTop, chartWidth - xStart, yGzBot - yGzTop);

                        // 61.8% Golden Pocket Line
                        const y618 = getY(sk.gz_618);
                        ctx.strokeStyle = '#f59e0b';
                        ctx.beginPath();
                        ctx.moveTo(xStart, y618);
                        ctx.lineTo(chartWidth, y618);
                        ctx.stroke();

                        ctx.fillStyle = '#f59e0b';
                        ctx.font = '10px sans-serif';
                        ctx.textAlign = 'right';
                        ctx.fillText('SK 61.8% GZ (' + sk.gz_618.toFixed(2) + ')', chartWidth - 8, y618 - 4);

                        // 161.8% Target
                        if (sk.target_1618) {{
                            const y1618 = getY(sk.target_1618);
                            ctx.strokeStyle = '#06b6d4';
                            ctx.beginPath();
                            ctx.moveTo(xStart, y1618);
                            ctx.lineTo(chartWidth, y1618);
                            ctx.stroke();
                            ctx.fillStyle = '#06b6d4';
                            ctx.fillText('TP 161.8% (' + sk.target_1618.toFixed(2) + ')', chartWidth - 8, y1618 - 4);
                        }}
                        ctx.setLineDash([]);
                    }}

                    // Render MSNR Key Levels
                    if (levels && levels.length > 0) {{
                        levels.forEach(lvl => {{
                            const yLvl = getY(lvl.price);
                            const isSupport = lvl.type === 'RBS' || lvl.type === 'KEY_SUPPORT';
                            const color = isSupport ? '#10b981' : '#ef4444';

                            ctx.strokeStyle = color;
                            ctx.lineWidth = 1;
                            ctx.beginPath();
                            ctx.moveTo(0, yLvl);
                            ctx.lineTo(chartWidth, yLvl);
                            ctx.stroke();

                            ctx.fillStyle = color;
                            ctx.font = '10px monospace';
                            ctx.textAlign = 'left';
                            ctx.fillText(lvl.type + ' ' + lvl.price.toFixed(2), chartWidth + 8, yLvl + 3);
                        }});
                    }}

                    // Render Active Signal Setup
                    if (signal && signal.entry) {{
                        const yEntry = getY(signal.entry);
                        const ySl = getY(signal.sl);
                        const yTp = getY(signal.tp1);
                        const isForming = (signal.status === 'FORMING');
                        const isCompleted = (signal.status === 'COMPLETED');
                        const isTp1Hit = (signal.status === 'TP1_HIT');

                        let entryColor = '#00e5ff';
                        let entryLabel = 'ACTIVATED: ACTIVE TRADE [ENTRY] ';
                        let tp1Label = 'TP1 ';
                        let slLabel = 'SL ';

                        if (isForming) {{
                            entryColor = '#ff9900';
                            entryLabel = 'ENTRY HERE [FORMING] ';
                            tp1Label = 'TP1 HERE ';
                            slLabel = 'SL HERE ';
                        }} else if (isTp1Hit) {{
                            entryColor = '#00e5ff';
                            entryLabel = 'ENTRY [BREAKEVEN SL] ';
                            tp1Label = '✅ TP1 HIT [RUNNER TO TP2] ';
                            slLabel = 'TRAILED SL (BREAKEVEN) ';
                        }} else if (isCompleted) {{
                            entryColor = '#8b949e';
                            entryLabel = 'ENTRY [TARGETS ACHIEVED] ';
                            tp1Label = '✅ ALL TPs HIT [COMPLETED] ';
                            slLabel = 'SL [CLOSED] ';
                        }}

                        // Entry Line
                        ctx.strokeStyle = entryColor;
                        ctx.lineWidth = 2;
                        if (isForming) ctx.setLineDash([5, 3]);
                        ctx.beginPath();
                        ctx.moveTo(0, yEntry);
                        ctx.lineTo(chartWidth, yEntry);
                        ctx.stroke();
                        ctx.setLineDash([]);

                        // Stop Loss Line
                        ctx.strokeStyle = '#ff1744';
                        ctx.lineWidth = 1.5;
                        ctx.setLineDash([4, 4]);
                        ctx.beginPath();
                        ctx.moveTo(0, ySl);
                        ctx.lineTo(chartWidth, ySl);
                        ctx.stroke();

                        // TP1 Line
                        ctx.strokeStyle = '#00e676';
                        ctx.beginPath();
                        ctx.moveTo(0, yTp);
                        ctx.lineTo(chartWidth, yTp);
                        ctx.stroke();
                        ctx.setLineDash([]);

                        // Labels
                        ctx.font = 'bold 11px monospace';
                        ctx.fillStyle = entryColor;
                        ctx.fillText(entryLabel + signal.entry.toFixed(2), 12, yEntry - 5);
                        ctx.fillStyle = '#ff1744';
                        ctx.fillText(slLabel + signal.sl.toFixed(2), 12, ySl + 12);
                        ctx.fillStyle = '#00e676';
                        ctx.fillText(tp1Label + signal.tp1.toFixed(2) + ' (R:R ' + signal.rr_tp1 + ':1)', 12, yTp - 5);
                    }}

                    // Render Volume Bars
                    for (let i = 0; i < candles.length; i++) {{
                        const c = candles[i];
                        const x = getX(i);
                        const isBullish = c.c >= c.o;
                        const vRatio = maxVol > 0 ? (c.v / maxVol) : 0.1;
                        const vBarH = vRatio * (volumeHeight - 10);
                        const vY = chartHeight - vBarH;

                        ctx.fillStyle = isBullish ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)';
                        ctx.fillRect(x - candleW / 2, vY, candleW, vBarH);
                    }}

                    // Render Candlesticks
                    for (let i = 0; i < candles.length; i++) {{
                        const c = candles[i];
                        const x = getX(i);
                        const yO = getY(c.o);
                        const yH = getY(c.h);
                        const yL = getY(c.l);
                        const yC = getY(c.c);

                        const isBullish = c.c >= c.o;
                        const color = isBullish ? '#10b981' : '#ef4444';

                        // Wick
                        ctx.strokeStyle = color;
                        ctx.lineWidth = 1.2;
                        ctx.beginPath();
                        ctx.moveTo(x, yH);
                        ctx.lineTo(x, yL);
                        ctx.stroke();

                        // Body
                        const bodyTop = Math.min(yO, yC);
                        const bodyHeight = Math.max(2, Math.abs(yC - yO));
                        ctx.fillStyle = color;
                        ctx.fillRect(x - candleW / 2, bodyTop, candleW, bodyHeight);
                    }}

                    // Crosshair on hover
                    if (hoverIndex >= 0 && hoverIndex < candles.length) {{
                        const hc = candles[hoverIndex];
                        const hx = getX(hoverIndex);
                        const hy = getY(hc.c);

                        ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
                        ctx.setLineDash([2, 2]);
                        ctx.beginPath();
                        ctx.moveTo(hx, 0);
                        ctx.lineTo(hx, chartHeight);
                        ctx.moveTo(0, hy);
                        ctx.lineTo(chartWidth, hy);
                        ctx.stroke();
                        ctx.setLineDash([]);

                        // Time pill at bottom
                        ctx.fillStyle = '#1f2937';
                        ctx.fillRect(hx - 45, chartHeight + 4, 90, 18);
                        ctx.fillStyle = '#f3f4f6';
                        ctx.font = '10px monospace';
                        ctx.textAlign = 'center';
                        ctx.fillText(hc.t.slice(5, 16), hx, chartHeight + 17);

                        // Price pill at right
                        ctx.fillStyle = '#1f2937';
                        ctx.fillRect(chartWidth + 2, hy - 9, 68, 18);
                        ctx.fillStyle = '#f3f4f6';
                        ctx.textAlign = 'left';
                        ctx.fillText(hc.c.toFixed(2), chartWidth + 6, hy + 4);

                        // Update header values
                        valO.innerText = hc.o.toFixed(2);
                        valH.innerText = hc.h.toFixed(2);
                        valL.innerText = hc.l.toFixed(2);
                        valC.innerText = hc.c.toFixed(2);
                        valV.innerText = hc.v.toLocaleString();
                    }} else {{
                        const last = candles[candles.length - 1];
                        valO.innerText = last.o.toFixed(2);
                        valH.innerText = last.h.toFixed(2);
                        valL.innerText = last.l.toFixed(2);
                        valC.innerText = last.c.toFixed(2);
                        valV.innerText = last.v.toLocaleString();
                    }}
                }}

                canvas.addEventListener('mousemove', function(e) {{
                    const rect = canvas.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const paddingRight = 75;
                    const chartWidth = width - paddingRight;

                    if (x >= 0 && x <= chartWidth) {{
                        const idx = Math.floor((x / chartWidth) * candles.length);
                        hoverIndex = Math.max(0, Math.min(candles.length - 1, idx));
                    }} else {{
                        hoverIndex = -1;
                    }}
                    draw();
                }});

                canvas.addEventListener('mouseleave', function() {{
                    hoverIndex = -1;
                    draw();
                }});

                window.addEventListener('resize', resize);
                resize();
            }})();
        </script>
    </body>
    </html>
    """
    return html


def render_tradingview_widget_html(symbol: str = "XAUUSD", timeframe: str = "15m", height: int = 560) -> str:
    """
    Generates the official TradingView Technical Analysis institutional widget.
    """
    tv_symbol_map = {
        "XAUUSD": "OANDA:XAUUSD",
        "EURUSD": "FX:EURUSD",
        "GBPUSD": "FX:GBPUSD",
        "BTCUSD": "COINBASE:BTCUSD"
    }
    tv_sym = tv_symbol_map.get(symbol.upper(), "OANDA:XAUUSD")
    tv_interval_map = {"15m": "15", "1h": "60", "4h": "240", "1d": "D"}
    tv_interval = tv_interval_map.get(timeframe.lower(), "15")

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;background:#0b0f19;">
        <div class="tradingview-widget-container" style="height:{height}px;width:100%;">
            <div id="tradingview_embed" style="height:100%;width:100%;"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget({{
                "autosize": true,
                "symbol": "{tv_sym}",
                "interval": "{tv_interval}",
                "timezone": "Etc/UTC",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "#0b0f19",
                "enable_publishing": false,
                "hide_side_toolbar": false,
                "allow_symbol_change": true,
                "container_id": "tradingview_embed"
            }});
            </script>
        </div>
    </body>
    </html>
    """
