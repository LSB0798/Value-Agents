"""Phase 2.5 OutcomeTracker 单元测试。"""
# ./tests/unit/test_outcome_tracker.py

import tempfile
from datetime import datetime, timezone, timedelta

import pytest

from valueagents.learning.outcome import OutcomeTracker
from valueagents.learning.recorder import record_decision, load_decisions


def test_judge_outcome_buy():
    """Buy 判定：涨 > 3% → right；跌 > 3% → wrong；中间 → neutral。"""
    assert OutcomeTracker._judge_outcome("Buy", 100.0, 110.0) == "right"
    assert OutcomeTracker._judge_outcome("Buy", 100.0, 90.0) == "wrong"
    assert OutcomeTracker._judge_outcome("Buy", 100.0, 101.5) == "neutral"


def test_judge_outcome_sell():
    """Sell 判定：跌 > 3% → right；涨 > 3% → wrong。"""
    assert OutcomeTracker._judge_outcome("Sell", 100.0, 90.0) == "right"
    assert OutcomeTracker._judge_outcome("Sell", 100.0, 110.0) == "wrong"
    assert OutcomeTracker._judge_outcome("Sell", 100.0, 99.0) == "neutral"


def test_judge_outcome_hold():
    """Hold 判定：横盘 ±5% → right。"""
    assert OutcomeTracker._judge_outcome("Hold", 100.0, 103.0) == "right"
    assert OutcomeTracker._judge_outcome("Hold", 100.0, 120.0) == "wrong"


def test_compute_master_accuracy_empty(tmp_path, monkeypatch):
    """无决策记录 → 空 dict。"""
    monkeypatch.setenv("VALUEAGENTS_DECISIONS_DIR", str(tmp_path))
    tracker = OutcomeTracker()
    acc = tracker.compute_master_accuracy()
    assert acc == {}


def test_backtest_mode_empty(tmp_path, monkeypatch):
    """无决策记录 → accuracy=None。"""
    monkeypatch.setenv("VALUEAGENTS_DECISIONS_DIR", str(tmp_path))
    tracker = OutcomeTracker()
    result = tracker.backtest_mode("legacy", ["B1"])
    assert result["total"] == 0
    assert result["accuracy"] is None


def test_daily_update_no_decisions(tmp_path, monkeypatch):
    """无决策记录 → 所有 stats=0。"""
    monkeypatch.setenv("VALUEAGENTS_DECISIONS_DIR", str(tmp_path))
    tracker = OutcomeTracker()
    stats = tracker.daily_update(today="2026-12-01")
    assert stats["updated_1m"] == 0
    assert stats["updated_3m"] == 0
    assert stats["updated_6m"] == 0
