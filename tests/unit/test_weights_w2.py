"""Phase 4 W2：pipeline 接入 MasterWeights 的单元测试。"""

from unittest.mock import patch, MagicMock

import pytest

from valueagents.agents.skills.core.research_team_skill.skill import (
    _apply_master_weights_if_enabled,
)
from valueagents.learning.weights import reset_default_weights


# ============================================================
# 1. 开关关闭（默认）：完全不调用 apply_weights_to_signals
# ============================================================
def test_disabled_by_default():
    """enabled=False → 不调 apply_weights_to_signals，返回原 dict。"""
    reset_default_weights()
    raw = {"buffett": {"signal": "bullish", "confidence": 80}}
    with patch(
        "valueagents.learning.weights.apply_weights_to_signals"
    ) as mock_apply:
        result = _apply_master_weights_if_enabled(raw, enabled=False)
        assert not mock_apply.called
        assert result is raw   # 同一个对象，不创建副本


def test_disabled_explicit():
    """enabled=False 显式传入 → 同上。"""
    reset_default_weights()
    raw = {"buffett": {"signal": "bullish", "confidence": 80}}
    with patch(
        "valueagents.learning.weights.apply_weights_to_signals"
    ) as mock_apply:
        result = _apply_master_weights_if_enabled(raw, enabled=False)
        assert not mock_apply.called
        assert result is raw


# ============================================================
# 2. 开关打开：调用 apply_weights_to_signals，返回调整后
# ============================================================
def test_enabled_calls_apply():
    """enabled=True → 调用 apply，返回 mock 的调整后结果。"""
    reset_default_weights()
    raw = {"buffett": {"signal": "bullish", "confidence": 80}}
    adjusted = {
        "buffett": {
            "signal": "bullish",
            "confidence": 40.0,
            "_raw_confidence": 80,
        }
    }
    with patch(
        "valueagents.learning.weights.apply_weights_to_signals",
        return_value=adjusted,
    ) as mock_apply:
        result = _apply_master_weights_if_enabled(raw, enabled=True)
        assert mock_apply.called
        assert result["buffett"]["confidence"] == 40.0


# ============================================================
# 3. 开关打开但空 signals：直接返回空
# ============================================================
def test_enabled_empty_signals():
    reset_default_weights()
    with patch(
        "valueagents.learning.weights.apply_weights_to_signals"
    ) as mock_apply:
        result = _apply_master_weights_if_enabled({}, enabled=True)
        assert not mock_apply.called
        assert result == {}


# ============================================================
# 4. 开关打开但 apply 抛异常：回退原 dict（不抛）
# ============================================================
def test_enabled_exception_fallback():
    """apply 抛异常 → 返回原 dict，不崩。"""
    reset_default_weights()
    raw = {"buffett": {"signal": "bullish", "confidence": 80}}
    with patch(
        "valueagents.learning.weights.apply_weights_to_signals",
        side_effect=RuntimeError("mock boom"),
    ):
        result = _apply_master_weights_if_enabled(raw, enabled=True)
        assert result is raw


# ============================================================
# 5. 不修改原 dict（无论开或关）
# ============================================================
def test_does_not_mutate_when_enabled():
    """开关打开时，原 dict 内容不变。"""
    reset_default_weights()
    raw = {"buffett": {"signal": "bullish", "confidence": 80}}
    raw_copy = {"buffett": {"signal": "bullish", "confidence": 80}}

    # 用一个会改变 confidence 的真实 apply
    # 通过 mock MasterWeights 让 multiplier=0.5
    from valueagents.learning.weights import MasterWeights
    fake_weights = MagicMock(spec=MasterWeights)
    fake_weights.get_effective_confidence.return_value = 0.4
    fake_weights.get_stats.return_value = None

    with patch(
        "valueagents.learning.weights._get_default_weights",
        return_value=fake_weights,
    ):
        result = _apply_master_weights_if_enabled(raw, enabled=True)
        # 原 dict 不变
        assert raw == raw_copy
        # 结果 dict 调整了
        assert result["buffett"]["confidence"] == pytest.approx(40.0)


# ============================================================
# 6. settings 集成：默认从 settings.enable_master_weights 读
# ============================================================
def test_reads_settings_when_enabled_none(monkeypatch):
    """enabled=None → 从 settings 读（默认 False）。"""
    reset_default_weights()
    from valueagents.settings import settings
    # 确保 settings.enable_master_weights 是 False（默认）
    # 用 monkeypatch 强制 False（防止环境变量污染）
    from dataclasses import replace
    monkeypatch.setattr(
        "valueagents.settings.settings",
        replace(settings, enable_master_weights=False),
    )

    raw = {"buffett": {"signal": "bullish", "confidence": 80}}
    with patch(
        "valueagents.learning.weights.apply_weights_to_signals"
    ) as mock_apply:
        # _apply_master_weights_if_enabled 内部是 `from valueagents.settings import settings`
        # 所以 monkeypatch 改 valueagents.settings.settings 生效
        result = _apply_master_weights_if_enabled(raw, enabled=None)
        assert not mock_apply.called
        assert result is raw
