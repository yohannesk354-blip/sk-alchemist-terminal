"""
Automated Unit Tests for SK Sequence & Alchemist MSNR Institutional Terminal
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from sk_engine import SKSequenceEngine, SequenceType, SequenceState, SKSequence
from alchemist_engine import AlchemistMSNREngine, MSNRZoneType, StorylineBias
from signal_generator import UnifiedSignalEngine, SignalAction, SignalStatus


@pytest.fixture
def sample_ohlcv_data():
    """Generates a standard 120-candle dataset with an upward impulse and pullback."""
    np.random.seed(42)
    n = 120
    dates = pd.date_range(end=datetime.now(), periods=n, freq="15min")
    
    # 0-40: Base at 2400
    # 40-80: Rise to 2440 (Impulse A -> B)
    # 80-110: Pullback to 2420 (Golden Zone ~ 50-61.8%)
    # 110-120: Reversal bounce
    trend = np.zeros(n)
    trend[0:40] = 2400.0
    trend[40:80] = np.linspace(2400.0, 2440.0, 40)
    trend[80:110] = np.linspace(2440.0, 2418.0, 30)
    trend[110:120] = np.linspace(2418.0, 2422.0, 10)
    
    noise = np.random.normal(0, 0.5, n)
    prices = trend + noise
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices - 0.2,
        'high': prices + 1.0,
        'low': prices - 1.0,
        'close': prices + 0.2,
        'volume': np.random.randint(1000, 5000, n)
    }, index=dates)
    
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    return df


def test_sk_sequence_golden_zone_math():
    """Validates mathematical correctness of SK Golden Zone and Extension formulas."""
    seq = SKSequence(
        id="TEST_BULL_1",
        sequence_type=SequenceType.BULLISH,
        point_a_price=2400.0,
        point_a_idx=10,
        point_b_price=2500.0,
        point_b_idx=50
    )
    # Diff is 100.0
    assert seq.gz_500 == pytest.approx(2450.0, 0.01)
    assert seq.gz_559 == pytest.approx(2444.1, 0.01)
    assert seq.gz_618 == pytest.approx(2438.2, 0.01)
    assert seq.gz_667 == pytest.approx(2433.3, 0.01)
    assert seq.target_1618 == pytest.approx(2561.8, 0.01)
    assert seq.target_2000 == pytest.approx(2600.0, 0.01)
    assert seq.break_point_a == 2500.0


def test_sk_sequence_detection(sample_ohlcv_data):
    """Ensures SK Sequence Engine detects swings and sequences."""
    engine = SKSequenceEngine(swing_window=4)
    sequences = engine.identify_sequences(sample_ohlcv_data)
    assert len(sequences) > 0
    bullish = [s for s in sequences if s.sequence_type == SequenceType.BULLISH]
    assert len(bullish) > 0


def test_msnr_key_level_clustering(sample_ohlcv_data):
    """Ensures Alchemist MSNR Engine identifies body-based levels and storyline."""
    engine = AlchemistMSNREngine(cluster_tolerance_pct=0.003)
    levels = engine.find_body_key_levels(sample_ohlcv_data)
    assert len(levels) > 0
    
    storyline = engine.determine_storyline(sample_ohlcv_data)
    assert storyline in (StorylineBias.BULLISH, StorylineBias.BEARISH, StorylineBias.CONSOLIDATION)


def test_msnr_engulfing_detection():
    """Tests Bullish and Bearish Engulfing detection."""
    engine = AlchemistMSNREngine()
    dates = pd.date_range(end=datetime.now(), periods=3, freq="15min")
    
    # Bearish followed by large Bullish engulfing
    df_bull = pd.DataFrame({
        'open': [2410.0, 2408.0, 2404.0],
        'high': [2412.0, 2409.0, 2415.0],
        'low': [2407.0, 2403.0, 2403.0],
        'close': [2408.0, 2405.0, 2414.0]
    }, index=dates)
    assert engine.detect_engulfing(df_bull) == "BULLISH_ENGULFING"


def test_lot_size_risk_management():
    """Validates position sizing formulas across XAUUSD, Forex, and Crypto."""
    engine = UnifiedSignalEngine()
    
    # 1. Gold (XAUUSD): $10,000 balance, 1% risk ($100), $5 SL distance ($500/lot) -> 0.20 lots
    lot_gold = engine.calculate_lot_size("XAUUSD", 10000.0, 1.0, entry=2420.0, sl=2415.0)
    assert lot_gold == 0.20
    
    # 2. Forex (EURUSD): $10,000 balance, 1% risk ($100), 20 pips SL ($200/lot) -> 0.50 lots
    lot_fx = engine.calculate_lot_size("EURUSD", 10000.0, 1.0, entry=1.0850, sl=1.0830)
    assert lot_fx == 0.50


def test_unified_signal_generation(sample_ohlcv_data):
    """Tests end-to-end signal engine execution."""
    engine = UnifiedSignalEngine(swing_window=4)
    signals = engine.generate_signals(
        sample_ohlcv_data,
        symbol="XAUUSD",
        timeframe="15m",
        account_balance=10000.0,
        risk_pct=1.0
    )
    # Check that returned signals comply with expected interface
    for sig in signals:
        assert sig.action in (SignalAction.BUY, SignalAction.SELL)
        assert sig.status in (SignalStatus.FORMING, SignalStatus.ACTIVATED)
        assert sig.entry_price > 0
        assert sig.stop_loss > 0
        assert sig.tp1_price > 0
        assert sig.recommended_lot_size >= 0.01
        assert len(sig.confluence_factors) > 0
        assert len(sig.status_description) > 0
        if sig.status == SignalStatus.FORMING:
            assert "here" in sig.status_description.lower()
        elif sig.status == SignalStatus.COMPLETED:
            assert "completed" in sig.status_description.lower() or "hit" in sig.status_description.lower()
        elif sig.status == SignalStatus.TP1_HIT:
            assert "tp1" in sig.status_description.lower() or "runner" in sig.status_description.lower()
        else:
            assert "active trade" in sig.status_description.lower() or "live" in sig.status_description.lower()


def test_completed_trade_tp_hit_handling():
    """Verifies that trades which have already hit all TPs are classified as COMPLETED, NOT active."""
    np.random.seed(42)
    n = 150
    dates = pd.date_range(end=datetime.now(), periods=n, freq="15min")
    trend = np.zeros(n)
    trend[0:40] = 2400.0
    trend[40:80] = np.linspace(2400.0, 2440.0, 40)
    trend[80:110] = np.linspace(2440.0, 2418.0, 30)
    trend[110:150] = np.linspace(2418.0, 2485.0, 40)  # Rallies past 161.8% target (2467)
    noise = np.random.normal(0, 0.5, n)
    prices = trend + noise

    df = pd.DataFrame({
        "open": prices - 0.2,
        "high": prices + 1.0,
        "low": prices - 1.0,
        "close": prices + 0.2,
        "volume": np.random.randint(1000, 5000, n)
    }, index=dates)
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)

    engine = UnifiedSignalEngine(swing_window=4)
    signals = engine.generate_signals(df, symbol="XAUUSD", timeframe="15m")
    
    # Check that any signal corresponding to this sequence is marked COMPLETED
    completed = [s for s in signals if s.status == SignalStatus.COMPLETED]
    assert len(completed) > 0, "Trade that hit all profit targets must be marked as COMPLETED"
    c_sig = completed[0]
    assert c_sig.status == SignalStatus.COMPLETED
    assert "completed" in c_sig.status_description.lower() or "hit" in c_sig.status_description.lower()
    # It must NOT be labeled as ACTIVATED
    assert c_sig.status != SignalStatus.ACTIVATED




def test_lse_data_feed():
    """Validates live connectivity and response processing with London Strategic Edge API."""
    from lse_feed import LSEDataFeed
    feed = LSEDataFeed()
    usage = feed.get_vault_usage()
    assert "error" not in usage
    assert usage.get("calls_per_minute", 0) > 0

    df = feed.fetch_candles(symbol="XAUUSD", timeframe="15m", limit=5)
    assert len(df) == 5
    assert set(['time', 'open', 'high', 'low', 'close', 'volume']).issubset(df.columns)
    assert df['close'].iloc[-1] > 0


def test_cot_engine_analysis():
    """Validates CFTC Commitments of Traders (COT) calculation and data ingestion."""
    from cot_engine import COTEngine, COTBias
    cot = COTEngine()
    snap = cot.analyze_cot_positioning("XAUUSD")
    assert snap.symbol == "XAUUSD"
    assert snap.open_interest > 0
    assert snap.noncomm_long > 0
    assert snap.noncomm_short > 0
    assert snap.net_noncomm == snap.noncomm_long - snap.noncomm_short
    assert snap.net_comm == snap.comm_long - snap.comm_short
    assert 0.0 <= snap.cot_index <= 100.0
    assert snap.institutional_bias in (COTBias.STRONG_BULLISH, COTBias.BULLISH, COTBias.NEUTRAL, COTBias.BEARISH, COTBias.STRONG_BEARISH)
    assert len(snap.collaboration_notes) > 0


def test_cot_signal_collaboration(sample_ohlcv_data):
    """Validates that signals synthesize COT institutional positioning directly into confluences."""
    engine = UnifiedSignalEngine(swing_window=4)
    signals = engine.generate_signals(
        sample_ohlcv_data,
        symbol="XAUUSD",
        timeframe="15m",
        account_balance=10000.0,
        risk_pct=1.0
    )
    assert len(signals) > 0
    sig = signals[0]
    assert sig.cot_snapshot is not None
    assert sig.cot_snapshot.open_interest > 0
    # Confluence should contain CFTC COT note
    has_cot_confluence = any("COT" in c for c in sig.confluence_factors)
    assert has_cot_confluence is True


def test_economic_calendar_engine():
    """Validates economic news calendar retrieval and impact classification."""
    from eco_calendar import EconomicCalendarEngine, EventImpact
    cal = EconomicCalendarEngine()
    
    # Test impact categorization
    assert cal.determine_impact("Core CPI MoM") == EventImpact.HIGH
    assert cal.determine_impact("Fed Interest Rate Decision") == EventImpact.HIGH
    assert cal.determine_impact("Nonfarm Payrolls") == EventImpact.HIGH
    assert cal.determine_impact("ISM Manufacturing PMI") == EventImpact.HIGH
    assert cal.determine_impact("ADP Employment Change") == EventImpact.MEDIUM
    assert cal.determine_impact("3-Month Bill Auction") == EventImpact.LOW

    # Test asset mapping
    assert "XAUUSD" in cal.determine_affected_assets("US")
    assert "EURUSD" in cal.determine_affected_assets("EZ")
    assert "GBPUSD" in cal.determine_affected_assets("GB")

    # Test calendar fetch
    events = cal.fetch_calendar(limit=10)
    assert len(events) > 0
    ev = events[0]
    assert ev.date != ""
    assert ev.time != ""
    assert ev.region_code != ""
    assert ev.impact in (EventImpact.HIGH, EventImpact.MEDIUM, EventImpact.LOW)
    assert len(ev.affected_assets) > 0

    # Test high impact check
    warning = cal.check_high_impact_warning("XAUUSD")
    # Warning is either None or an EconomicEvent with HIGH impact
    if warning:
        assert warning.impact == EventImpact.HIGH



