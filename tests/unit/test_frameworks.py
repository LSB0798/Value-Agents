# ./tests/unit/test_frameworks.py
"""Phase 3 W1 frameworks 单元测试。"""

import pytest

from valueagents.evidence import (
    ALL_19_MASTERS,
    MASTER_GROUPS,
    FRAMEWORK_QUESTIONS,
    FRAMEWORK_APPLICABLE_WHEN,
    FrameworkView,
    build_framework_views,
    summarize_framework_views,
)


# ============================================================
# 1. MASTER_GROUPS 完整性
# ============================================================
def test_master_groups_cover_all_19():
    """8 个 group 覆盖 19 个 master，无遗漏、无重复。"""
    flat = [m for group in MASTER_GROUPS.values() for m in group]
    assert len(flat) == len(set(flat)), "有重复 master"
    assert set(flat) == ALL_19_MASTERS, f"遗漏或多余: {set(flat) ^ ALL_19_MASTERS}"


def test_all_groups_have_question_and_applicability():
    """每个 group 都有 question 和 applicable_when。"""
    for gid in MASTER_GROUPS:
        assert gid in FRAMEWORK_QUESTIONS, f"{gid} 缺 question"
        assert gid in FRAMEWORK_APPLICABLE_WHEN, f"{gid} 缺 applicable_when"


# ============================================================
# 2. 空输入
# ============================================================
def test_empty_signals_returns_empty():
    assert build_framework_views({}) == []
    assert build_framework_views({}, enabled_groups=["intrinsic_value"]) == []


# ============================================================
# 3. 单 master（tail_risk / macro_momentum / technical）
# ============================================================
def test_single_master_bullish():
    signals = {
        "nassim_taleb_analyst": {"signal": "bullish", "confidence": 80},
    }
    views = build_framework_views(signals)
    assert len(views) == 1
    v = views[0]
    assert v.framework_id == "tail_risk"
    assert v.verdict == "bullish"
    assert v.confidence == pytest.approx(0.80)
    assert v.contributing_masters == ["nassim_taleb_analyst"]
    assert v.total_masters_in_group == 1


def test_single_master_neutral():
    signals = {"technical_analyst": {"signal": "neutral", "confidence": 55}}
    views = build_framework_views(signals)
    assert len(views) == 1
    assert views[0].verdict == "neutral"


# ============================================================
# 4. 多 master 多数投票
# ============================================================
def test_multi_master_majority_bullish():
    """intrinsic_value: 4 master 里 2 bullish / 1 bearish / 1 neutral → bullish。"""
    signals = {
        "warren_buffett_analyst": {"signal": "bullish", "confidence": 85},
        "charlie_munger_analyst": {"signal": "neutral", "confidence": 50},
        "ben_graham_analyst": {"signal": "bearish", "confidence": 72},
        "aswath_damodaran_analyst": {"signal": "bullish", "confidence": 70},
    }
    views = build_framework_views(signals)
    assert len(views) == 1
    v = views[0]
    assert v.framework_id == "intrinsic_value"
    assert v.verdict == "bullish"
    # 只有 bullish master 的 confidence 平均：(85 + 70) / 2 / 100 = 0.775
    assert v.confidence == pytest.approx(0.775)
    assert set(v.contributing_masters) == {"warren_buffett_analyst", "aswath_damodaran_analyst"}
    assert v.total_masters_in_group == 4


def test_multi_master_tie_neutral():
    """平局 → neutral。"""
    signals = {
        "warren_buffett_analyst": {"signal": "bullish", "confidence": 80},
        "ben_graham_analyst": {"signal": "bearish", "confidence": 80},
    }
    views = build_framework_views(signals, enabled_groups=["intrinsic_value"])
    assert len(views) == 1
    assert views[0].verdict == "neutral"


def test_multi_master_partial_data():
    """intrinsic_value 4 个 master 只有 2 个有 signal → total=2。"""
    signals = {
        "warren_buffett_analyst": {"signal": "bullish", "confidence": 80},
        "charlie_munger_analyst": {"signal": "bullish", "confidence": 60},
    }
    views = build_framework_views(signals, enabled_groups=["intrinsic_value"])
    assert len(views) == 1
    v = views[0]
    assert v.verdict == "bullish"
    assert v.total_masters_in_group == 2  # 只统计有数据的


# ============================================================
# 5. 双层 signal 兼容
# ============================================================
def test_double_layer_signal_format():
    """{ticker: {signal, confidence}} 格式兼容。"""
    signals = {
        "warren_buffett_analyst": {
            "NFLX": {"signal": "bullish", "confidence": 82},
        },
        "ben_graham_analyst": {
            "NFLX": {"signal": "bearish", "confidence": 72},
        },
    }
    views = build_framework_views(signals, enabled_groups=["intrinsic_value"])
    assert len(views) == 1
    # 平局 → neutral
    assert views[0].verdict == "neutral"


# ============================================================
# 6. enabled_groups 过滤
# ============================================================
def test_enabled_groups_filter():
    signals = {
        "warren_buffett_analyst": {"signal": "bullish", "confidence": 80},
        "technical_analyst": {"signal": "bearish", "confidence": 60},
    }
    # 只构建 intrinsic_value
    views = build_framework_views(signals, enabled_groups=["intrinsic_value"])
    assert len(views) == 1
    assert views[0].framework_id == "intrinsic_value"

    # 两个都构建
    views = build_framework_views(signals)
    assert len(views) == 2
    ids = {v.framework_id for v in views}
    assert ids == {"intrinsic_value", "technical"}


# ============================================================
# 7. 无数据 group 不返回
# ============================================================
def test_missing_group_not_returned():
    """只有 tail_risk 有数据 → 只返回 1 个 view。"""
    signals = {"nassim_taleb_analyst": {"signal": "neutral", "confidence": 50}}
    views = build_framework_views(signals)
    assert len(views) == 1
    assert views[0].framework_id == "tail_risk"


# ============================================================
# 8. summarize_framework_views
# ============================================================
def test_summarize_empty():
    assert summarize_framework_views([]) == "(no framework views)"


def test_summarize_contains_keywords():
    signals = {
        "warren_buffett_analyst": {"signal": "bullish", "confidence": 80},
        "nassim_taleb_analyst": {"signal": "neutral", "confidence": 50},
    }
    views = build_framework_views(signals)
    text = summarize_framework_views(views)
    assert "intrinsic_value" in text
    assert "tail_risk" in text
    assert "bullish" in text


def test_agent_suffix_compatible():
    """_agent 结尾的 master_signals 也能被识别（修复 W2 发现的 bug）。"""
    # 模拟 SIGNAL AGGREGATOR 的实际输出格式
    signals = {
        "warren_buffett_agent": {"signal": "bullish", "confidence": 85},
        "charlie_munger_agent": {"signal": "neutral", "confidence": 50},
        "ben_graham_agent": {"signal": "bearish", "confidence": 72},
    }
    views = build_framework_views(signals)
    assert len(views) == 1, f"期望 1 个 view，实际 {len(views)} 个"
    v = views[0]
    assert v.framework_id == "intrinsic_value"
    assert v.verdict == "neutral"   # 1 bull / 1 bear / 1 neutral → 平局
    assert v.total_masters_in_group == 3


def test_mixed_suffix_compatible():
    """混合 _agent 和 _analyst 也能被识别。"""
    signals = {
        "warren_buffett_agent": {"signal": "bullish", "confidence": 85},   # _agent
        "charlie_munger_analyst": {"signal": "neutral", "confidence": 50},  # _analyst
        "ben_graham_agent": {"signal": "bearish", "confidence": 72},        # _agent
    }
    views = build_framework_views(signals)
    assert len(views) == 1
    assert views[0].total_masters_in_group == 3


def test_no_duplicate_when_both_suffixes_present():
    """同一个 master 两个命名都有时，只计一次（不重复投票）。"""
    signals = {
        "warren_buffett_analyst": {"signal": "bullish", "confidence": 85},
        "warren_buffett_agent": {"signal": "bullish", "confidence": 85},
    }
    views = build_framework_views(signals, enabled_groups=["intrinsic_value"])
    assert len(views) == 1
    # 只计 1 次（intrinsic_value group 有 4 master，只有 1 个有数据）
    assert views[0].total_masters_in_group == 1