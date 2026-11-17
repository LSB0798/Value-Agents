# ./tests/unit/test_weights.py
"""Phase 4 W1 MasterWeights 单元测试。"""

from unittest.mock import patch, MagicMock

import pytest

from valueagents.learning.weights import (
    MasterWeights,
    apply_weights_to_signals,
    reset_default_weights,
)


# ============================================================
# 辅助：mock OutcomeTracker.compute_master_accuracy
# ============================================================
def _mock_tracker(stats: dict):
    """构造一个 mock tracker 返回固定 stats。"""
    tracker = MagicMock()
    tracker.compute_master_accuracy.return_value = stats
    return tracker


def _make_weights_with_stats(stats: dict, min_samples: int = 30) -> MasterWeights:
    """构造一个已加载指定 stats 的 MasterWeights。"""
    w = MasterWeights(min_samples=min_samples)
    with patch("valueagents.learning.outcome.OutcomeTracker", return_value=_mock_tracker(stats)):
        w.compute_weights()
    return w


# ============================================================
# 1. 数据不足：回退 raw_confidence
# ============================================================
def test_insufficient_samples_returns_raw():
    w = _make_weights_with_stats({
        "buffett": {"n": 5, "accuracy": 0.9},  # n < 30
    })
    assert w.get_effective_confidence("buffett", 0.8) == 0.8


def test_no_stats_returns_raw():
    w = _make_weights_with_stats({})
    assert w.get_effective_confidence("unknown", 0.7) == 0.7


# ============================================================
# 2. 数据充足：调整 confidence
# ============================================================
def test_high_accuracy_boosts_confidence():
    """accuracy=0.75 → multiplier = 1.5 → 0.8 * 1.5 = 1.2 → clip 到 1.0。"""
    w = _make_weights_with_stats({
        "buffett": {"n": 50, "accuracy": 0.75},
    })
    assert w.get_effective_confidence("buffett", 0.8) == 1.0  # clip


def test_low_accuracy_reduces_confidence():
    """accuracy=0.25 → multiplier = 0.5 → 0.8 * 0.5 = 0.4。"""
    w = _make_weights_with_stats({
        "burry": {"n": 50, "accuracy": 0.25},
    })
    assert w.get_effective_confidence("burry", 0.8) == pytest.approx(0.4)


def test_baseline_accuracy_unchanged():
    """accuracy=0.5 → multiplier = 1.0 → 不变。"""
    w = _make_weights_with_stats({
        "munger": {"n": 50, "accuracy": 0.5},
    })
    assert w.get_effective_confidence("munger", 0.7) == pytest.approx(0.7)


# ============================================================
# 3. multiplier 边界
# ============================================================
def test_multiplier_upper_bound():
    """accuracy=0.9 → 1.8 → clip 到 1.5 → 0.6 * 1.5 = 0.9。"""
    w = _make_weights_with_stats({
        "buffett": {"n": 50, "accuracy": 0.9},
    })
    assert w.get_effective_confidence("buffett", 0.6) == pytest.approx(0.9)


def test_multiplier_lower_bound():
    """accuracy=0.1 → 0.2 → clip 到 0.5 → 0.8 * 0.5 = 0.4。"""
    w = _make_weights_with_stats({
        "burry": {"n": 50, "accuracy": 0.1},
    })
    assert w.get_effective_confidence("burry", 0.8) == pytest.approx(0.4)


def test_final_confidence_clipped_to_1():
    """raw=0.9, accuracy=0.9 → 0.9 * 1.5 = 1.35 → clip 到 1.0。"""
    w = _make_weights_with_stats({
        "buffett": {"n": 50, "accuracy": 0.9},
    })
    assert w.get_effective_confidence("buffett", 0.9) == 1.0


# ============================================================
# 4. apply_weights_to_signals：单层格式
# ============================================================
def test_apply_single_layer():
    """单层 {master: {signal, confidence}} 被正确调整。"""
    w = _make_weights_with_stats({
        "warren_buffett_agent": {"n": 50, "accuracy": 0.25},  # multiplier 0.5
    })
    signals = {
        "warren_buffett_agent": {
            "signal": "bullish",
            "confidence": 80,
            "reasoning": "test",
        }
    }
    result = apply_weights_to_signals(signals, weights=w)
    entry = result["warren_buffett_agent"]
    assert entry["signal"] == "bullish"
    assert entry["confidence"] == pytest.approx(40.0)  # 80 * 0.5
    assert entry["_raw_confidence"] == 80


# ============================================================
# 5. apply_weights_to_signals：双层格式
# ============================================================
def test_apply_double_layer():
    """双层 {master: {ticker: {signal, confidence}}} 被正确调整。"""
    w = _make_weights_with_stats({
        "warren_buffett_agent": {"n": 50, "accuracy": 0.75},  # multiplier 1.5
    })
    signals = {
        "warren_buffett_agent": {
            "NFLX": {"signal": "bullish", "confidence": 60},
        }
    }
    result = apply_weights_to_signals(signals, weights=w)
    ticker_sig = result["warren_buffett_agent"]["NFLX"]
    assert ticker_sig["confidence"] == pytest.approx(90.0)  # 60 * 1.5
    assert ticker_sig["_raw_confidence"] == 60


# ============================================================
# 6. 空输入
# ============================================================
def test_apply_empty_signals():
    w = _make_weights_with_stats({})
    assert apply_weights_to_signals({}, weights=w) == {}


# ============================================================
# 7. 不修改原 dict
# ============================================================
def test_apply_does_not_mutate_input():
    w = _make_weights_with_stats({})
    original = {
        "buffett": {"signal": "bullish", "confidence": 80},
    }
    original_copy = {
        "buffett": {"signal": "bullish", "confidence": 80},
    }
    apply_weights_to_signals(original, weights=w)
    assert original == original_copy


# ============================================================
# 8. 数据不足时不影响
# ============================================================
def test_apply_insufficient_samples_no_change():
    w = _make_weights_with_stats({
        "buffett": {"n": 5, "accuracy": 0.9},  # n < 30
    })
    signals = {
        "buffett": {"signal": "bullish", "confidence": 80},
    }
    result = apply_weights_to_signals(signals, weights=w)
    assert result["buffett"]["confidence"] == 80


# ============================================================
# 9. reset_default_weights
# ============================================================
def test_reset_default_weights():
    reset_default_weights()
    from valueagents.learning.weights import _get_default_weights
    w1 = _get_default_weights()
    reset_default_weights()
    w2 = _get_default_weights()
    assert w1 is not w2


def test_scale_0_100_clip():
    """scale='0-100' 时按 0-100 范围 clip（不裁到 1.0）。"""
    w = _make_weights_with_stats({
        "buffett": {"n": 50, "accuracy": 0.9},   # multiplier=1.5
    })
    # raw=90 → 90*1.5=135 → clip 到 100
    assert w.get_effective_confidence("buffett", 90, scale="0-100") == pytest.approx(100.0)
    # raw=40 → 40*1.5=60 → 不触发 clip
    assert w.get_effective_confidence("buffett", 40, scale="0-100") == pytest.approx(60.0)


def test_scale_0_1_default_unchanged():
    """默认 scale='0-1' 行为不变。"""
    w = _make_weights_with_stats({
        "buffett": {"n": 50, "accuracy": 0.9},
    })
    # raw=0.9 → 1.35 → clip 到 1.0
    assert w.get_effective_confidence("buffett", 0.9) == pytest.approx(1.0)