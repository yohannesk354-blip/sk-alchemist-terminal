"""
Alchemist MSNR Engine (Malaysian Support & Resistance)
Implements candle-body structural key levels, RBS/SBR breakout & retest mechanics,
engulfing confirmations, liquidity wicks, and storyline bias.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict
import pandas as pd
import numpy as np


class MSNRZoneType(str, Enum):
    RBS = "RBS"                      # Resistance Becomes Support
    SBR = "SBR"                      # Support Becomes Resistance
    KEY_SUPPORT = "KEY_SUPPORT"      # Fresh Support
    KEY_RESISTANCE = "KEY_RESISTANCE"# Fresh Resistance


class StorylineBias(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    CONSOLIDATION = "CONSOLIDATION"


@dataclass
class MSNRLevel:
    id: str
    price: float             # Primary level (body open/close cluster)
    zone_top: float          # Upper boundary (incorporating wicks)
    zone_bottom: float       # Lower boundary
    zone_type: MSNRZoneType
    formed_idx: int
    retest_count: int = 0
    is_fresh: bool = True
    strength_score: float = 1.0


@dataclass
class MSNRConfluence:
    has_level_reaction: bool
    active_level: Optional[MSNRLevel]
    is_engulfing_confirmed: bool
    engulfing_type: Optional[str] # "BULLISH_ENGULFING", "BEARISH_ENGULFING"
    has_liquidity_wick: bool
    storyline_bias: StorylineBias
    notes: List[str] = field(default_factory=list)


class AlchemistMSNREngine:
    """
    Malaysian Support & Resistance (MSNR) Engine.
    Emphasizes candlestick body levels, RBS/SBR flips, rejection wicks,
    and storyline market context.
    """

    def __init__(self, cluster_tolerance_pct: float = 0.0015, min_retests: int = 1):
        self.cluster_tolerance_pct = cluster_tolerance_pct
        self.min_retests = min_retests

    def find_body_key_levels(self, df: pd.DataFrame) -> List[MSNRLevel]:
        """
        Extracts key horizontal levels based on candlestick bodies (open/close).
        Groups nearby levels into tight Malaysian SNR zones.
        """
        if len(df) < 10:
            return []

        opens = df['open'].values
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        n = len(df)

        # Collect body edges
        body_levels = []
        for i in range(n):
            body_top = max(opens[i], closes[i])
            body_bot = min(opens[i], closes[i])
            body_levels.append((body_top, i, highs[i], lows[i]))
            body_levels.append((body_bot, i, highs[i], lows[i]))

        # Sort and cluster levels
        body_levels.sort(key=lambda x: x[0])
        clusters: List[List[Tuple[float, int, float, float]]] = []

        for item in body_levels:
            if not clusters:
                clusters.append([item])
            else:
                last_avg = np.mean([x[0] for x in clusters[-1]])
                if abs(item[0] - last_avg) / (last_avg + 1e-9) <= self.cluster_tolerance_pct:
                    clusters[-1].append(item)
                else:
                    clusters.append([item])

        current_price = df['close'].iloc[-1]
        levels: List[MSNRLevel] = []

        for idx, cluster in enumerate(clusters):
            if len(cluster) < 2:
                continue

            prices = [x[0] for x in cluster]
            mean_price = float(np.mean(prices))
            earliest_idx = min(x[1] for x in cluster)
            
            # Wicks in cluster
            cluster_highs = [x[2] for x in cluster]
            cluster_lows = [x[3] for x in cluster]
            zone_top = float(max(cluster_highs))
            zone_bottom = float(min(cluster_lows))

            # Determine initial zone type
            if mean_price < current_price:
                zone_type = MSNRZoneType.KEY_SUPPORT
            else:
                zone_type = MSNRZoneType.KEY_RESISTANCE

            # Calculate retests after earliest formation
            retests = 0
            for i in range(earliest_idx + 1, n):
                if zone_bottom <= lows[i] <= zone_top or zone_bottom <= highs[i] <= zone_top:
                    retests += 1

            level = MSNRLevel(
                id=f"MSNR_{idx}_{round(mean_price, 2)}",
                price=round(mean_price, 4),
                zone_top=round(zone_top, 4),
                zone_bottom=round(zone_bottom, 4),
                zone_type=zone_type,
                formed_idx=earliest_idx,
                retest_count=retests,
                is_fresh=(retests <= 2),
                strength_score=min(3.0, 1.0 + 0.3 * len(cluster))
            )
            levels.append(level)

        return levels

    def detect_rbs_sbr(self, df: pd.DataFrame, levels: List[MSNRLevel]) -> List[MSNRLevel]:
        """
        Refines key levels into RBS (Resistance Becomes Support) or SBR (Support Becomes Resistance)
        based on breakout and subsequent retest behavior.
        """
        current_price = df['close'].iloc[-1]
        refined: List[MSNRLevel] = []

        for lvl in levels:
            formed = lvl.formed_idx
            if formed >= len(df) - 3:
                refined.append(lvl)
                continue

            post_df = df.iloc[formed:]
            had_break_above = (post_df['close'] > lvl.price * 1.0015).any()
            had_break_below = (post_df['close'] < lvl.price * 0.9985).any()

            # RBS: Broke above a previous resistance and now trading at or above it
            if had_break_above and current_price >= lvl.zone_bottom * 0.999:
                lvl.zone_type = MSNRZoneType.RBS
            # SBR: Broke below a previous support and now trading at or below it
            elif had_break_below and current_price <= lvl.zone_top * 1.001:
                lvl.zone_type = MSNRZoneType.SBR

            refined.append(lvl)

        return refined

    def detect_engulfing(self, df: pd.DataFrame, lookback: int = 3) -> Optional[str]:
        """
        Detects Bullish or Bearish Engulfing pattern on recent candles.
        """
        if len(df) < 2:
            return None

        for offset in range(1, min(lookback + 1, len(df))):
            curr = df.iloc[-offset]
            prev = df.iloc[-offset - 1]

            curr_open, curr_close = curr['open'], curr['close']
            prev_open, prev_close = prev['open'], prev['close']

            curr_bullish = curr_close > curr_open
            prev_bearish = prev_close < prev_open

            curr_bearish = curr_close < curr_open
            prev_bullish = prev_close > prev_open

            # Bullish Engulfing
            if curr_bullish and prev_bearish:
                if curr_close >= prev_open and curr_open <= prev_close:
                    return "BULLISH_ENGULFING"

            # Bearish Engulfing
            if curr_bearish and prev_bullish:
                if curr_close <= prev_open and curr_open >= prev_close:
                    return "BEARISH_ENGULFING"

        return None

    def detect_liquidity_wick(self, df: pd.DataFrame, level: MSNRLevel) -> bool:
        """
        Detects if recent candles swept liquidity beyond the level but body closed inside.
        """
        if len(df) < 2:
            return False

        last_candles = df.iloc[-3:]
        for _, c in last_candles.iterrows():
            body_min = min(c['open'], c['close'])
            body_max = max(c['open'], c['close'])

            # Pierced below level zone with wick, but body closed inside or above
            if c['low'] < level.zone_bottom and body_min >= level.zone_bottom:
                return True
            # Pierced above level zone with wick, but body closed inside or below
            if c['high'] > level.zone_top and body_max <= level.zone_top:
                return True

        return False

    def determine_storyline(self, df: pd.DataFrame) -> StorylineBias:
        """
        Evaluates higher timeframe storyline bias using EMA momentum and structure.
        """
        if len(df) < 20:
            return StorylineBias.CONSOLIDATION

        closes = df['close']
        ema_short = closes.ewm(span=9, adjust=False).mean().iloc[-1]
        ema_mid = closes.ewm(span=21, adjust=False).mean().iloc[-1]
        ema_long = closes.ewm(span=50, adjust=False).mean().iloc[-1] if len(df) >= 50 else closes.mean()

        if ema_short > ema_mid and closes.iloc[-1] >= ema_mid:
            return StorylineBias.BULLISH
        elif ema_short < ema_mid and closes.iloc[-1] <= ema_mid:
            return StorylineBias.BEARISH
        else:
            return StorylineBias.CONSOLIDATION

    def evaluate_confluence(self, df: pd.DataFrame, target_price: Optional[float] = None) -> MSNRConfluence:
        """
        Calculates all MSNR structural components for current market state.
        """
        current_price = target_price or df['close'].iloc[-1]
        raw_levels = self.find_body_key_levels(df)
        levels = self.detect_rbs_sbr(df, raw_levels)
        storyline = self.determine_storyline(df)
        engulfing = self.detect_engulfing(df)

        active_level = None
        min_dist = float('inf')
        for lvl in levels:
            dist = abs(current_price - lvl.price)
            if dist < min_dist and dist / lvl.price < 0.015:
                min_dist = dist
                active_level = lvl

        has_reaction = active_level is not None
        has_wick = self.detect_liquidity_wick(df, active_level) if active_level else False

        notes = []
        if active_level:
            notes.append(f"MSNR {active_level.zone_type.value} Key Level at {active_level.price:.2f}")
        if engulfing:
            notes.append(f"Institutional Confirmation: {engulfing.replace('_', ' ').title()}")
        if has_wick:
            notes.append("Liquidity Sweep / Rejection Wick Detected")
        notes.append(f"Storyline Bias: {storyline.value}")

        return MSNRConfluence(
            has_level_reaction=has_reaction,
            active_level=active_level,
            is_engulfing_confirmed=(engulfing is not None),
            engulfing_type=engulfing,
            has_liquidity_wick=has_wick,
            storyline_bias=storyline,
            notes=notes
        )
