"""
Stefan Kassing (SK) Sequence Engine
Mathematical implementation of SK trend structures, Golden Zones, and Fibonacci extension targets.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np


class SequenceType(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class SequenceState(str, Enum):
    FORMING = "FORMING"
    IN_GOLDEN_ZONE = "IN_GOLDEN_ZONE"
    TRIGGERED = "TRIGGERED"
    COMPLETED = "COMPLETED"
    INVALIDATED = "INVALIDATED"


@dataclass
class SKSequence:
    id: str
    sequence_type: SequenceType
    point_a_price: float
    point_a_idx: int
    point_b_price: float
    point_b_idx: int
    point_c_price: Optional[float] = None
    point_c_idx: Optional[int] = None
    
    # Golden Zone Retracement Levels (50.0% to 66.7%)
    gz_500: float = 0.0
    gz_559: float = 0.0
    gz_618: float = 0.0
    gz_667: float = 0.0
    
    # Extension Profit Targets
    target_1618: float = 0.0
    target_2000: float = 0.0
    
    # Risk Invalidation
    invalidation_level: float = 0.0
    state: SequenceState = SequenceState.FORMING
    break_point_a: float = 0.0  # High of B in bullish, Low of B in bearish
    
    def __post_init__(self):
        diff = abs(self.point_b_price - self.point_a_price)
        if self.sequence_type == SequenceType.BULLISH:
            self.gz_500 = self.point_b_price - (0.500 * diff)
            self.gz_559 = self.point_b_price - (0.559 * diff)
            self.gz_618 = self.point_b_price - (0.618 * diff)
            self.gz_667 = self.point_b_price - (0.667 * diff)
            self.target_1618 = self.point_a_price + (1.618 * diff)
            self.target_2000 = self.point_a_price + (2.000 * diff)
            self.invalidation_level = self.point_a_price
            self.break_point_a = self.point_b_price
        else:
            self.gz_500 = self.point_b_price + (0.500 * diff)
            self.gz_559 = self.point_b_price + (0.559 * diff)
            self.gz_618 = self.point_b_price + (0.618 * diff)
            self.gz_667 = self.point_b_price + (0.667 * diff)
            self.target_1618 = self.point_a_price - (1.618 * diff)
            self.target_2000 = self.point_a_price - (2.000 * diff)
            self.invalidation_level = self.point_a_price
            self.break_point_a = self.point_b_price


class SKSequenceEngine:
    """
    Engine to identify Stefan Kassing A-B impulses, BC corrections,
    Golden Zone tests, and extension completions.
    """

    def __init__(self, swing_window: int = 5, min_impulse_atr_mult: float = 1.2):
        self.swing_window = swing_window
        self.min_impulse_atr_mult = min_impulse_atr_mult

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        tr1 = high - low
        tr2 = (high - close).abs()
        tr3 = (low - close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean().bfill()

    def detect_swings(self, df: pd.DataFrame) -> Tuple[List[Tuple[int, float, str]], List[Tuple[int, float, str]]]:
        """
        Identifies local swing highs and swing lows using a rolling window.
        Returns (swing_highs, swing_lows) as lists of (index_pos, price, type).
        """
        highs = df['high'].values
        lows = df['low'].values
        n = len(df)
        w = max(2, self.swing_window)

        swing_highs = []
        swing_lows = []

        for i in range(w, n - w):
            # Check if local peak
            is_high = True
            for j in range(i - w, i + w + 1):
                if j != i and highs[j] >= highs[i]:
                    is_high = False
                    break
            if is_high:
                swing_highs.append((i, highs[i], "HIGH"))

            # Check if local trough
            is_low = True
            for j in range(i - w, i + w + 1):
                if j != i and lows[j] <= lows[i]:
                    is_low = False
                    break
            if is_low:
                swing_lows.append((i, lows[i], "LOW"))

        return swing_highs, swing_lows

    def identify_sequences(self, df: pd.DataFrame) -> List[SKSequence]:
        """
        Scans dataframe for active and recent SK Sequences.
        """
        if len(df) < self.swing_window * 3:
            return []

        atr = self.calculate_atr(df).iloc[-1]
        swing_highs, swing_lows = self.detect_swings(df)
        
        # Merge swings chronologically
        all_swings = sorted(swing_highs + swing_lows, key=lambda x: x[0])
        sequences: List[SKSequence] = []
        
        # Search for impulse legs A -> B
        for i in range(len(all_swings) - 1):
            s1 = all_swings[i]
            s2 = all_swings[i + 1]

            # Bullish sequence: Low (A) -> High (B)
            if s1[2] == "LOW" and s2[2] == "HIGH":
                diff = s2[1] - s1[1]
                if diff >= atr * self.min_impulse_atr_mult:
                    seq = SKSequence(
                        id=f"BULL_{s1[0]}_{s2[0]}",
                        sequence_type=SequenceType.BULLISH,
                        point_a_price=float(s1[1]),
                        point_a_idx=s1[0],
                        point_b_price=float(s2[1]),
                        point_b_idx=s2[0],
                    )
                    self._update_sequence_state(seq, df)
                    sequences.append(seq)

            # Bearish sequence: High (A) -> Low (B)
            elif s1[2] == "HIGH" and s2[2] == "LOW":
                diff = s1[1] - s2[1]
                if diff >= atr * self.min_impulse_atr_mult:
                    seq = SKSequence(
                        id=f"BEAR_{s1[0]}_{s2[0]}",
                        sequence_type=SequenceType.BEARISH,
                        point_a_price=float(s1[1]),
                        point_a_idx=s1[0],
                        point_b_price=float(s2[1]),
                        point_b_idx=s2[0],
                    )
                    self._update_sequence_state(seq, df)
                    sequences.append(seq)

        return sequences

    def _update_sequence_state(self, seq: SKSequence, df: pd.DataFrame):
        """
        Tracks price development after Point B to verify if:
        1. Price pulled back into Golden Zone (50% - 66.7%)
        2. Price breached invalidation
        3. Price triggered a breakout of Point B towards target
        4. Price reached 161.8% or 200% target
        """
        n = len(df)
        if seq.point_b_idx >= n - 1:
            seq.state = SequenceState.FORMING
            return

        post_b = df.iloc[seq.point_b_idx + 1:]
        current_price = df['close'].iloc[-1]
        
        if seq.sequence_type == SequenceType.BULLISH:
            min_low_after_b = post_b['low'].min()
            max_high_after_b = post_b['high'].max()
            
            # Check if invalidated
            if min_low_after_b < seq.invalidation_level or min_low_after_b < seq.gz_667 * 0.998:
                seq.state = SequenceState.INVALIDATED
                return
            
            # Check if targets completed
            if max_high_after_b >= seq.target_1618:
                seq.state = SequenceState.COMPLETED
                return
            
            # Check if currently or recently in Golden Zone
            # Golden Zone is between gz_500 and gz_667
            in_gz = (seq.gz_667 <= current_price <= seq.gz_500) or (seq.gz_667 <= min_low_after_b <= seq.gz_500 and current_price >= seq.gz_667)
            if in_gz:
                seq.state = SequenceState.IN_GOLDEN_ZONE
                # Record lowest point reached as C
                c_idx = post_b['low'].idxmin()
                seq.point_c_price = float(min_low_after_b)
                seq.point_c_idx = df.index.get_loc(c_idx) if c_idx in df.index else seq.point_b_idx + 1
            elif min_low_after_b <= seq.gz_500 and current_price > seq.gz_500:
                seq.state = SequenceState.TRIGGERED
            else:
                seq.state = SequenceState.FORMING

        else: # BEARISH
            max_high_after_b = post_b['high'].max()
            min_low_after_b = post_b['low'].min()
            
            # Check if invalidated
            if max_high_after_b > seq.invalidation_level or max_high_after_b > seq.gz_667 * 1.002:
                seq.state = SequenceState.INVALIDATED
                return
            
            # Check if target hit
            if min_low_after_b <= seq.target_1618:
                seq.state = SequenceState.COMPLETED
                return

            # Check Golden Zone
            in_gz = (seq.gz_500 <= current_price <= seq.gz_667) or (seq.gz_500 <= max_high_after_b <= seq.gz_667 and current_price <= seq.gz_667)
            if in_gz:
                seq.state = SequenceState.IN_GOLDEN_ZONE
                c_idx = post_b['high'].idxmax()
                seq.point_c_price = float(max_high_after_b)
                seq.point_c_idx = df.index.get_loc(c_idx) if c_idx in df.index else seq.point_b_idx + 1
            elif max_high_after_b >= seq.gz_500 and current_price < seq.gz_500:
                seq.state = SequenceState.TRIGGERED
            else:
                seq.state = SequenceState.FORMING

    def get_most_relevant_sequence(self, df: pd.DataFrame) -> Optional[SKSequence]:
        """
        Returns the active or in-golden-zone sequence closest to current price action.
        """
        sequences = self.identify_sequences(df)
        active = [s for s in sequences if s.state in (SequenceState.IN_GOLDEN_ZONE, SequenceState.TRIGGERED)]
        if active:
            return active[-1]
        forming = [s for s in sequences if s.state == SequenceState.FORMING]
        if forming:
            return forming[-1]
        return sequences[-1] if sequences else None
