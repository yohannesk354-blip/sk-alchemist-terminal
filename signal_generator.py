"""
Unified Signal Engine
Combines Stefan Kassing (SK) Sequences with Alchemist MSNR (Malaysian Support & Resistance)
to produce institutional trade setups with distinct 'FORMING' and 'ACTIVATED' states,
exact entry/tp/sl targets, risk parameters, and lot sizing.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import pandas as pd
import numpy as np

from sk_engine import SKSequenceEngine, SKSequence, SequenceType, SequenceState
from alchemist_engine import AlchemistMSNREngine, MSNRConfluence, MSNRZoneType, StorylineBias
from cot_engine import COTEngine, COTSnapshot, COTBias


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStatus(str, Enum):
    FORMING = "FORMING"        # Setup is forming / pending entry: Entry here, TP here, SL here
    ACTIVATED = "ACTIVATED"    # Activated an active trade: Position is live (targets pending)
    TP1_HIT = "TP1_HIT"        # TP1 has been hit! Runner position active targeting TP2 (SL at Breakeven)
    COMPLETED = "COMPLETED"    # All Take Profits Hit! Trade cycle complete (targets reached)


@dataclass
class TradeSignal:
    action: SignalAction
    symbol: str
    status: SignalStatus
    entry_price: float
    stop_loss: float
    tp1_price: float
    rr_tp1: float
    tp2_price: float
    rr_tp2: float
    recommended_lot_size: float
    risk_amount_usd: float
    confluence_factors: List[str]
    status_description: str = ""
    cot_snapshot: Optional[COTSnapshot] = None
    timeframe: str = "15m"
    timestamp: Optional[pd.Timestamp] = None


class UnifiedSignalEngine:
    """
    Synthesizes Stefan Kassing (SK) Fibonacci Sequences, Alchemist MSNR body levels,
    CFTC Commitments of Traders (COT) hedge fund net positioning, and structural story lines.
    Produces high-probability institutional trading tickets with exact sizing and precise status.
    """

    def __init__(self, swing_window: int = 5, api_key: Optional[str] = None):
        self.sk_engine = SKSequenceEngine(swing_window=swing_window)
        self.msnr_engine = AlchemistMSNREngine()
        self.cot_engine = COTEngine(api_key=api_key)

    def calculate_lot_size(
        self,
        symbol: str,
        account_balance: float,
        risk_pct: float,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        entry: Optional[float] = None,
        sl: Optional[float] = None
    ) -> float:
        """
        Calculates institutional standard lot size based on percentage account risk.
        Lot Size = Risk ($) / (Risk Distance * Contract Multiplier)
        """
        actual_entry = entry_price if entry_price is not None else entry
        actual_sl = stop_loss if stop_loss is not None else sl
        if actual_entry is None or actual_sl is None:
            return 0.01

        risk_usd = account_balance * (risk_pct / 100.0)
        risk_dist = abs(actual_entry - actual_sl)
        if risk_dist <= 0:
            return 0.01

        sym = symbol.upper()
        if "XAU" in sym:
            multiplier = 100.0       # 100 oz per standard lot
        elif "BTC" in sym:
            multiplier = 1.0         # 1 BTC per contract
        elif "EUR" in sym or "GBP" in sym:
            multiplier = 100000.0    # Standard FX lot = 100,000 units
        else:
            multiplier = 100.0

        lot_size = risk_usd / (risk_dist * multiplier)
        return max(0.01, round(lot_size, 2))

    def generate_signals(
        self,
        df: pd.DataFrame,
        symbol: str = "XAUUSD",
        timeframe: str = "15m",
        account_balance: float = 10000.0,
        risk_pct: float = 1.0
    ) -> List[TradeSignal]:
        """
        Main signal generation entry point called by the Streamlit dashboard.
        Accurately differentiates:
        1. FORMING: Pending Golden Zone entry
        2. ACTIVATED: Active trade triggered (targets pending)
        3. TP1_HIT: TP1 reached, runner open towards TP2 with SL at breakeven
        4. COMPLETED: Both TP1 and TP2 hit, trade cycle finished
        """
        if len(df) < 20:
            return []

        current_price = float(df['close'].iloc[-1])
        sequences = self.sk_engine.identify_sequences(df)
        msnr_conf = self.msnr_engine.evaluate_confluence(df, target_price=current_price)
        cot_snap = self.cot_engine.analyze_cot_positioning(symbol)

        active_signals: List[TradeSignal] = []
        completed_signals: List[TradeSignal] = []

        # Iterate from newest sequence to oldest sequence so fresh setups take precedence
        for seq in reversed(sequences):
            # ----------------- Check for Bullish Setups -----------------
            if seq.sequence_type == SequenceType.BULLISH:
                post_b = df.iloc[seq.point_b_idx + 1:] if seq.point_b_idx < len(df) - 1 else df.iloc[-1:]
                min_low_after_b = post_b['low'].min() if not post_b.empty else current_price
                max_high_after_b = post_b['high'].max() if not post_b.empty else current_price
                
                # Check invalidation (Stop Loss breached)
                if min_low_after_b < seq.gz_667 * 0.998 or min_low_after_b < seq.invalidation_level:
                    continue

                # Planned entry at 61.8% Golden Pocket or MSNR RBS level
                ideal_entry = seq.gz_618
                if msnr_conf.active_level and msnr_conf.active_level.zone_type in (MSNRZoneType.RBS, MSNRZoneType.KEY_SUPPORT):
                    ideal_entry = msnr_conf.active_level.price

                sl = min(seq.gz_667 * 0.998, seq.point_a_price * 0.999)
                risk_dist = ideal_entry - sl
                if risk_dist <= 0:
                    continue

                tp1 = max(seq.break_point_a, ideal_entry + (risk_dist * 2.5))
                tp2 = seq.target_1618
                rr1 = round((tp1 - ideal_entry) / risk_dist, 2)
                rr2 = round((tp2 - ideal_entry) / risk_dist, 2)
                lot_size = self.calculate_lot_size(symbol, account_balance, risk_pct, ideal_entry, sl)
                risk_usd = account_balance * (risk_pct / 100.0)

                # Has price touched the Golden Zone (50%-66.7%)?
                has_entered_gz = (min_low_after_b <= seq.gz_500 * 1.001)

                # Check if TP1 or TP2 have been reached
                has_hit_tp2 = (max_high_after_b >= tp2 * 0.999) or (current_price >= tp2 * 0.999) or (seq.state == SequenceState.COMPLETED)
                has_hit_tp1 = (max_high_after_b >= tp1 * 0.999) or (current_price >= tp1 * 0.999)

                # Condition 1: COMPLETED (All TPs hit)
                if has_entered_gz and has_hit_tp2:
                    confluences = [
                        f"SK Bullish Sequence (A: {seq.point_a_price:.2f} -> B: {seq.point_b_price:.2f})",
                        f"All Targets Reached: TP1 ({tp1:.2f}) & TP2 ({tp2:.2f}) Achieved",
                        f"Captured +{rr2}R Full Institutional Reward"
                    ]
                    sig = TradeSignal(
                        action=SignalAction.BUY,
                        symbol=symbol,
                        status=SignalStatus.COMPLETED,
                        entry_price=round(ideal_entry, 2),
                        stop_loss=round(sl, 2),
                        tp1_price=round(tp1, 2),
                        rr_tp1=rr1,
                        tp2_price=round(tp2, 2),
                        rr_tp2=rr2,
                        recommended_lot_size=lot_size,
                        risk_amount_usd=risk_usd,
                        confluence_factors=confluences,
                        status_description=f"Trade completed! All take profits have been hit. Both TP1 ({tp1:.2f}) and TP2 ({tp2:.2f}) were reached (+{rr2}R profit). Position is closed.",
                        cot_snapshot=cot_snap,
                        timeframe=timeframe,
                        timestamp=df.index[-1] if hasattr(df.index, 'tz') or isinstance(df.index, pd.DatetimeIndex) else None
                    )
                    completed_signals.append(sig)

                # Condition 2: TP1 HIT (Runner active towards TP2)
                elif has_entered_gz and has_hit_tp1:
                    confluences = [
                        f"SK Bullish Sequence (A: {seq.point_a_price:.2f} -> B: {seq.point_b_price:.2f})",
                        f"TP1 Target Reached at {tp1:.2f} (+{rr1}R Banked)",
                        f"Runner Active Targeting TP2 ({tp2:.2f}) with SL moved to Breakeven ({ideal_entry:.2f})"
                    ]
                    if msnr_conf.active_level:
                        confluences.append(f"MSNR {msnr_conf.active_level.zone_type.value} Level at {msnr_conf.active_level.price:.2f}")
                    sig = TradeSignal(
                        action=SignalAction.BUY,
                        symbol=symbol,
                        status=SignalStatus.TP1_HIT,
                        entry_price=round(ideal_entry, 2),
                        stop_loss=round(ideal_entry, 2),
                        tp1_price=round(tp1, 2),
                        rr_tp1=rr1,
                        tp2_price=round(tp2, 2),
                        rr_tp2=rr2,
                        recommended_lot_size=lot_size,
                        risk_amount_usd=risk_usd,
                        confluence_factors=confluences,
                        status_description=f"TP1 hit at {tp1:.2f} (+{rr1}R profit locked)! Runner position is active targeting TP2 ({tp2:.2f}). Stop Loss is trailed to breakeven ({ideal_entry:.2f}). Current price is {current_price:.2f}.",
                        cot_snapshot=cot_snap,
                        timeframe=timeframe,
                        timestamp=df.index[-1] if hasattr(df.index, 'tz') or isinstance(df.index, pd.DatetimeIndex) else None
                    )
                    active_signals.append(sig)
                    break

                # Condition 3: ACTIVATED (Active Trade — Targets Pending)
                elif has_entered_gz and (current_price >= ideal_entry * 0.999 or msnr_conf.is_engulfing_confirmed):
                    confluences = [
                        f"SK Bullish Sequence (A: {seq.point_a_price:.2f} -> B: {seq.point_b_price:.2f})",
                        f"BC Pullback tested Golden Zone (Low reached: {min_low_after_b:.2f})"
                    ]
                    if msnr_conf.active_level:
                        confluences.append(f"MSNR {msnr_conf.active_level.zone_type.value} Level at {msnr_conf.active_level.price:.2f}")
                    if msnr_conf.is_engulfing_confirmed:
                        confluences.append("Bullish Engulfing Reaction Confirmed")
                    if msnr_conf.storyline_bias == StorylineBias.BULLISH:
                        confluences.append("Storyline Momentum Aligned (Bullish)")
                    if cot_snap:
                        if cot_snap.institutional_bias in (COTBias.STRONG_BULLISH, COTBias.BULLISH):
                            confluences.append(f"CFTC COT Confluence: Speculators Net Long ({cot_snap.net_noncomm:+,d}, Index: {cot_snap.cot_index}%)")
                        elif cot_snap.institutional_bias in (COTBias.STRONG_BEARISH, COTBias.BEARISH):
                            confluences.append(f"⚠️ COT Divergence Warning: Speculators Net Short ({cot_snap.net_noncomm:+,d})")

                    sig = TradeSignal(
                        action=SignalAction.BUY,
                        symbol=symbol,
                        status=SignalStatus.ACTIVATED,
                        entry_price=round(ideal_entry, 2),
                        stop_loss=round(sl, 2),
                        tp1_price=round(tp1, 2),
                        rr_tp1=rr1,
                        tp2_price=round(tp2, 2),
                        rr_tp2=rr2,
                        recommended_lot_size=lot_size,
                        risk_amount_usd=risk_usd,
                        confluence_factors=confluences,
                        status_description=f"Active trade is live. Entry was at {ideal_entry:.2f}, current price is {current_price:.2f}. Holding for TP1 ({tp1:.2f}) & TP2 ({tp2:.2f}) with SL at {sl:.2f}.",
                        cot_snapshot=cot_snap,
                        timeframe=timeframe,
                        timestamp=df.index[-1] if hasattr(df.index, 'tz') or isinstance(df.index, pd.DatetimeIndex) else None
                    )
                    active_signals.append(sig)
                    break

                # Condition 4: FORMING (Setup Developing)
                elif current_price > seq.gz_500:
                    confluences = [
                        f"SK Bullish Sequence (A: {seq.point_a_price:.2f} -> B: {seq.point_b_price:.2f})",
                        f"Retracement forming towards Golden Zone [50%: {seq.gz_500:.2f} | 61.8%: {seq.gz_618:.2f}]"
                    ]
                    if msnr_conf.storyline_bias == StorylineBias.BULLISH:
                        confluences.append("Storyline Bullish Bias")
                    if cot_snap:
                        if cot_snap.institutional_bias in (COTBias.STRONG_BULLISH, COTBias.BULLISH):
                            confluences.append(f"CFTC COT Confluence: Speculators Net Long ({cot_snap.net_noncomm:+,d})")
                        elif cot_snap.institutional_bias in (COTBias.STRONG_BEARISH, COTBias.BEARISH):
                            confluences.append(f"⚠️ COT Divergence: Speculators Net Short ({cot_snap.net_noncomm:+,d})")

                    sig = TradeSignal(
                        action=SignalAction.BUY,
                        symbol=symbol,
                        status=SignalStatus.FORMING,
                        entry_price=round(ideal_entry, 2),
                        stop_loss=round(sl, 2),
                        tp1_price=round(tp1, 2),
                        rr_tp1=rr1,
                        tp2_price=round(tp2, 2),
                        rr_tp2=rr2,
                        recommended_lot_size=lot_size,
                        risk_amount_usd=risk_usd,
                        confluence_factors=confluences,
                        status_description=f"Setup is forming. Wait for price to pull back to entry here: {ideal_entry:.2f}, TP1 here: {tp1:.2f}, TP2 here: {tp2:.2f}, SL here: {sl:.2f}.",
                        cot_snapshot=cot_snap,
                        timeframe=timeframe,
                        timestamp=df.index[-1] if hasattr(df.index, 'tz') or isinstance(df.index, pd.DatetimeIndex) else None
                    )
                    active_signals.append(sig)
                    break

            # ----------------- Check for Bearish Setups -----------------
            elif seq.sequence_type == SequenceType.BEARISH:
                post_b = df.iloc[seq.point_b_idx + 1:] if seq.point_b_idx < len(df) - 1 else df.iloc[-1:]
                max_high_after_b = post_b['high'].max() if not post_b.empty else current_price
                min_low_after_b = post_b['low'].min() if not post_b.empty else current_price

                # Check invalidation (Stop Loss breached)
                if max_high_after_b > seq.gz_667 * 1.002 or max_high_after_b > seq.invalidation_level:
                    continue

                ideal_entry = seq.gz_618
                if msnr_conf.active_level and msnr_conf.active_level.zone_type in (MSNRZoneType.SBR, MSNRZoneType.KEY_RESISTANCE):
                    ideal_entry = msnr_conf.active_level.price

                sl = max(seq.gz_667 * 1.002, seq.point_a_price * 1.001)
                risk_dist = sl - ideal_entry
                if risk_dist <= 0:
                    continue

                tp1 = min(seq.break_point_a, ideal_entry - (risk_dist * 2.5))
                tp2 = seq.target_1618
                rr1 = round((ideal_entry - tp1) / risk_dist, 2)
                rr2 = round((ideal_entry - tp2) / risk_dist, 2)
                lot_size = self.calculate_lot_size(symbol, account_balance, risk_pct, ideal_entry, sl)
                risk_usd = account_balance * (risk_pct / 100.0)

                has_entered_gz = (max_high_after_b >= seq.gz_500 * 0.999)

                # Check if TP1 or TP2 have been reached
                has_hit_tp2 = (min_low_after_b <= tp2 * 1.001) or (current_price <= tp2 * 1.001) or (seq.state == SequenceState.COMPLETED)
                has_hit_tp1 = (min_low_after_b <= tp1 * 1.001) or (current_price <= tp1 * 1.001)

                # Condition 1: COMPLETED (All TPs hit)
                if has_entered_gz and has_hit_tp2:
                    confluences = [
                        f"SK Bearish Sequence (A: {seq.point_a_price:.2f} -> B: {seq.point_b_price:.2f})",
                        f"All Targets Reached: TP1 ({tp1:.2f}) & TP2 ({tp2:.2f}) Achieved",
                        f"Captured +{rr2}R Full Institutional Reward"
                    ]
                    sig = TradeSignal(
                        action=SignalAction.SELL,
                        symbol=symbol,
                        status=SignalStatus.COMPLETED,
                        entry_price=round(ideal_entry, 2),
                        stop_loss=round(sl, 2),
                        tp1_price=round(tp1, 2),
                        rr_tp1=rr1,
                        tp2_price=round(tp2, 2),
                        rr_tp2=rr2,
                        recommended_lot_size=lot_size,
                        risk_amount_usd=risk_usd,
                        confluence_factors=confluences,
                        status_description=f"Trade completed! All take profits have been hit. Both TP1 ({tp1:.2f}) and TP2 ({tp2:.2f}) were reached (+{rr2}R profit). Position is closed.",
                        cot_snapshot=cot_snap,
                        timeframe=timeframe,
                        timestamp=df.index[-1] if hasattr(df.index, 'tz') or isinstance(df.index, pd.DatetimeIndex) else None
                    )
                    completed_signals.append(sig)

                # Condition 2: TP1 HIT (Runner active towards TP2)
                elif has_entered_gz and has_hit_tp1:
                    confluences = [
                        f"SK Bearish Sequence (A: {seq.point_a_price:.2f} -> B: {seq.point_b_price:.2f})",
                        f"TP1 Target Reached at {tp1:.2f} (+{rr1}R Banked)",
                        f"Runner Active Targeting TP2 ({tp2:.2f}) with SL moved to Breakeven ({ideal_entry:.2f})"
                    ]
                    if msnr_conf.active_level:
                        confluences.append(f"MSNR {msnr_conf.active_level.zone_type.value} Level at {msnr_conf.active_level.price:.2f}")
                    sig = TradeSignal(
                        action=SignalAction.SELL,
                        symbol=symbol,
                        status=SignalStatus.TP1_HIT,
                        entry_price=round(ideal_entry, 2),
                        stop_loss=round(ideal_entry, 2),
                        tp1_price=round(tp1, 2),
                        rr_tp1=rr1,
                        tp2_price=round(tp2, 2),
                        rr_tp2=rr2,
                        recommended_lot_size=lot_size,
                        risk_amount_usd=risk_usd,
                        confluence_factors=confluences,
                        status_description=f"TP1 hit at {tp1:.2f} (+{rr1}R profit locked)! Runner position is active targeting TP2 ({tp2:.2f}). Stop Loss is trailed to breakeven ({ideal_entry:.2f}). Current price is {current_price:.2f}.",
                        cot_snapshot=cot_snap,
                        timeframe=timeframe,
                        timestamp=df.index[-1] if hasattr(df.index, 'tz') or isinstance(df.index, pd.DatetimeIndex) else None
                    )
                    active_signals.append(sig)
                    break

                # Condition 3: ACTIVATED (Active Trade — Targets Pending)
                elif has_entered_gz and (current_price <= ideal_entry * 1.001 or msnr_conf.is_engulfing_confirmed):
                    confluences = [
                        f"SK Bearish Sequence (A: {seq.point_a_price:.2f} -> B: {seq.point_b_price:.2f})",
                        f"BC Pullback tested Golden Zone (High reached: {max_high_after_b:.2f})"
                    ]
                    if msnr_conf.active_level:
                        confluences.append(f"MSNR {msnr_conf.active_level.zone_type.value} Level at {msnr_conf.active_level.price:.2f}")
                    if msnr_conf.is_engulfing_confirmed:
                        confluences.append("Bearish Engulfing Reaction Confirmed")
                    if msnr_conf.storyline_bias == StorylineBias.BEARISH:
                        confluences.append("Storyline Momentum Aligned (Bearish)")
                    if cot_snap:
                        if cot_snap.institutional_bias in (COTBias.STRONG_BEARISH, COTBias.BEARISH):
                            confluences.append(f"CFTC COT Confluence: Speculators Net Short ({cot_snap.net_noncomm:+,d}, Index: {cot_snap.cot_index}%)")
                        elif cot_snap.institutional_bias in (COTBias.STRONG_BULLISH, COTBias.BULLISH):
                            confluences.append(f"⚠️ COT Divergence Warning: Speculators Net Long ({cot_snap.net_noncomm:+,d})")

                    sig = TradeSignal(
                        action=SignalAction.SELL,
                        symbol=symbol,
                        status=SignalStatus.ACTIVATED,
                        entry_price=round(ideal_entry, 2),
                        stop_loss=round(sl, 2),
                        tp1_price=round(tp1, 2),
                        rr_tp1=rr1,
                        tp2_price=round(tp2, 2),
                        rr_tp2=rr2,
                        recommended_lot_size=lot_size,
                        risk_amount_usd=risk_usd,
                        confluence_factors=confluences,
                        status_description=f"Active trade is live. Entry was at {ideal_entry:.2f}, current price is {current_price:.2f}. Holding for TP1 ({tp1:.2f}) & TP2 ({tp2:.2f}) with SL at {sl:.2f}.",
                        cot_snapshot=cot_snap,
                        timeframe=timeframe,
                        timestamp=df.index[-1] if hasattr(df.index, 'tz') or isinstance(df.index, pd.DatetimeIndex) else None
                    )
                    active_signals.append(sig)
                    break

                # Condition 4: FORMING (Setup Developing)
                elif current_price < seq.gz_500:
                    confluences = [
                        f"SK Bearish Sequence (A: {seq.point_a_price:.2f} -> B: {seq.point_b_price:.2f})",
                        f"Retracement forming towards Golden Zone [50%: {seq.gz_500:.2f} | 61.8%: {seq.gz_618:.2f}]"
                    ]
                    if msnr_conf.storyline_bias == StorylineBias.BEARISH:
                        confluences.append("Storyline Bearish Bias")
                    if cot_snap:
                        if cot_snap.institutional_bias in (COTBias.STRONG_BEARISH, COTBias.BEARISH):
                            confluences.append(f"CFTC COT Confluence: Speculators Net Short ({cot_snap.net_noncomm:+,d})")
                        elif cot_snap.institutional_bias in (COTBias.STRONG_BULLISH, COTBias.BULLISH):
                            confluences.append(f"⚠️ COT Divergence: Speculators Net Long ({cot_snap.net_noncomm:+,d})")

                    sig = TradeSignal(
                        action=SignalAction.SELL,
                        symbol=symbol,
                        status=SignalStatus.FORMING,
                        entry_price=round(ideal_entry, 2),
                        stop_loss=round(sl, 2),
                        tp1_price=round(tp1, 2),
                        rr_tp1=rr1,
                        tp2_price=round(tp2, 2),
                        rr_tp2=rr2,
                        recommended_lot_size=lot_size,
                        risk_amount_usd=risk_usd,
                        confluence_factors=confluences,
                        status_description=f"Setup is forming. Wait for price to rally to entry here: {ideal_entry:.2f}, TP1 here: {tp1:.2f}, TP2 here: {tp2:.2f}, SL here: {sl:.2f}.",
                        cot_snapshot=cot_snap,
                        timeframe=timeframe,
                        timestamp=df.index[-1] if hasattr(df.index, 'tz') or isinstance(df.index, pd.DatetimeIndex) else None
                    )
                    active_signals.append(sig)
                    break

        # Fallback if no full sequence but strong MSNR Engulfing occurs at Key Level
        if not active_signals and not completed_signals and msnr_conf.has_level_reaction and msnr_conf.is_engulfing_confirmed:
            lvl = msnr_conf.active_level
            atr = self.sk_engine.calculate_atr(df).iloc[-1]
            if msnr_conf.engulfing_type == "BULLISH_ENGULFING" and lvl.zone_type in (MSNRZoneType.RBS, MSNRZoneType.KEY_SUPPORT):
                entry = current_price
                sl = lvl.zone_bottom - (atr * 0.8)
                risk_dist = entry - sl
                if risk_dist > 0:
                    tp1 = entry + (risk_dist * 3.0)
                    tp2 = entry + (risk_dist * 5.0)
                    lot_size = self.calculate_lot_size(symbol, account_balance, risk_pct, entry, sl)
                    active_signals.append(TradeSignal(
                        action=SignalAction.BUY,
                        symbol=symbol,
                        status=SignalStatus.ACTIVATED,
                        entry_price=round(entry, 2),
                        stop_loss=round(sl, 2),
                        tp1_price=round(tp1, 2),
                        rr_tp1=3.0,
                        tp2_price=round(tp2, 2),
                        rr_tp2=5.0,
                        recommended_lot_size=lot_size,
                        risk_amount_usd=account_balance * (risk_pct / 100.0),
                        confluence_factors=[
                            f"Alchemist MSNR {lvl.zone_type.value} Body Level at {lvl.price:.2f}",
                            "Bullish Engulfing Rejection Confirmation",
                            f"Storyline Bias: {msnr_conf.storyline_bias.value}"
                        ],
                        status_description=f"Activated active trade. MSNR confirmation at {lvl.price:.2f}. Entry: {entry:.2f}, SL: {sl:.2f}, TP1: {tp1:.2f}, TP2: {tp2:.2f}.",
                        timeframe=timeframe
                    ))
            elif msnr_conf.engulfing_type == "BEARISH_ENGULFING" and lvl.zone_type in (MSNRZoneType.SBR, MSNRZoneType.KEY_RESISTANCE):
                entry = current_price
                sl = lvl.zone_top + (atr * 0.8)
                risk_dist = sl - entry
                if risk_dist > 0:
                    tp1 = entry - (risk_dist * 3.0)
                    tp2 = entry - (risk_dist * 5.0)
                    lot_size = self.calculate_lot_size(symbol, account_balance, risk_pct, entry, sl)
                    active_signals.append(TradeSignal(
                        action=SignalAction.SELL,
                        symbol=symbol,
                        status=SignalStatus.ACTIVATED,
                        entry_price=round(entry, 2),
                        stop_loss=round(sl, 2),
                        tp1_price=round(tp1, 2),
                        rr_tp1=3.0,
                        tp2_price=round(tp2, 2),
                        rr_tp2=5.0,
                        recommended_lot_size=lot_size,
                        risk_amount_usd=account_balance * (risk_pct / 100.0),
                        confluence_factors=[
                            f"Alchemist MSNR {lvl.zone_type.value} Body Level at {lvl.price:.2f}",
                            "Bearish Engulfing Rejection Confirmation",
                            f"Storyline Bias: {msnr_conf.storyline_bias.value}"
                        ],
                        status_description=f"Activated active trade. MSNR confirmation at {lvl.price:.2f}. Entry: {entry:.2f}, SL: {sl:.2f}, TP1: {tp1:.2f}, TP2: {tp2:.2f}.",
                        timeframe=timeframe
                    ))

        return active_signals + completed_signals[:2]
