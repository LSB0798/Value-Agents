# ./tests/unit/test_risk_profile.py
"""Phase 3 W3a RiskProfile 单元测试。"""

import pytest

from valueagents.evidence import (
    DimensionSignal,
    FrameworkView,
    RiskProfile,
    build_risk_profile,
    summarize_risk_profile,
)


# ============================================================
# 辅助构造
# ============================================================
def _make_bundle(signals: list[dict]) -> dict:
    """模拟 EvidenceBundle.model_dump() 的最小结构。"""
    return {"signals": signals, "evidence": [], "claims": []}


def _sig(direction: str, strength: float = 0.7) -> dict:
    return {
        "ticker": "NFLX",
        "dimension": "any",
        "framework": None,
        "direction": direction,
        "strength": strength,
        "claim_ids": ["cl_test"],
        "provenance": "test",
    }


def _fw(fw_id: str, verdict: str, conf: float, n_masters: int = 1) -> FrameworkView:
    return FrameworkView(
        framework_id=fw_id,
        core_question="test",
        verdict=verdict,  # type: ignore
        confidence=conf,
        contributing_masters=["master_1"] * n_masters,
        total_masters_in_group=n_masters,
        key_uncertainty="",
        applicable_when="",
        claims=[],
    )


# ============================================================
# 1. 空输入
# ============================================================
def test_empty_all_neutral():
    """空 evidence + 空 framework → 5 维度全 neutral，rating=Hold。"""
    rp = build_risk_profile("NFLX", "2026-09-03", {}, [])
    assert rp.rating == "Hold"
    assert rp.overall_verdict == "neutral"
    assert rp.overall_score == pytest.approx(0.0)
    for name in ("trend", "valuation", "tail_risk", "catalyst", "sentiment"):
        d = rp.dimension_map()[name]
        assert d.direction == "neutral"
        assert d.strength == 0.0


# ============================================================
# 2. 单维度 bullish
# ============================================================
def test_single_dimension_bullish():
    """market 全 bullish → trend=bullish，其他 neutral。"""
    eg = {"market": _make_bundle([_sig("bullish", 0.8)])}
    rp = build_risk_profile("NFLX", "2026-09-03", eg, [])
    assert rp.trend.direction == "bullish"
    assert rp.trend.strength == pytest.approx(0.8)
    assert rp.valuation.direction == "neutral"
    assert rp.catalyst.direction == "neutral"
    assert rp.sentiment.direction == "neutral"


def test_all_dimensions_bullish_gives_buy():
    """5 维度全 bullish 且强 → Buy。"""
    eg = {
        "market":       _make_bundle([_sig("bullish", 0.9)]),
        "fundamentals": _make_bundle([_sig("bullish", 0.9)]),
        "news":         _make_bundle([_sig("bullish", 0.9)]),
        "sentiment":    _make_bundle([_sig("bullish", 0.9)]),
    }
    fw = [_fw("tail_risk", "bullish", 0.9, 1)]
    rp = build_risk_profile("NFLX", "2026-09-03", eg, fw)
    assert rp.rating == "Buy"
    assert rp.overall_verdict == "bullish"
    assert rp.overall_score > 0.4


def test_all_dimensions_bearish_gives_sell():
    eg = {
        "market":       _make_bundle([_sig("bearish", 0.9)]),
        "fundamentals": _make_bundle([_sig("bearish", 0.9)]),
        "news":         _make_bundle([_sig("bearish", 0.9)]),
        "sentiment":    _make_bundle([_sig("bearish", 0.9)]),
    }
    fw = [_fw("tail_risk", "bearish", 0.9, 1)]
    rp = build_risk_profile("NFLX", "2026-09-03", eg, fw)
    assert rp.rating == "Sell"
    assert rp.overall_verdict == "bearish"
    assert rp.overall_score < -0.4


# ============================================================
# 3. 多数投票
# ============================================================
def test_majority_vote_in_dimension():
    """market: 2 bull + 1 bear → trend=bullish。"""
    eg = {"market": _make_bundle([
        _sig("bullish", 0.8),
        _sig("bullish", 0.6),
        _sig("bearish", 0.7),
    ])}
    rp = build_risk_profile("NFLX", "2026-09-03", eg, [])
    assert rp.trend.direction == "bullish"
    # strength = mean(0.8, 0.6) = 0.7
    assert rp.trend.strength == pytest.approx(0.7)
    assert rp.trend.contributing_signals == 3


def test_tie_becomes_neutral():
    """1 bull + 1 bear → neutral。"""
    eg = {"market": _make_bundle([
        _sig("bullish", 0.8),
        _sig("bearish", 0.8),
    ])}
    rp = build_risk_profile("NFLX", "2026-09-03", eg, [])
    assert rp.trend.direction == "neutral"


# ============================================================
# 4. tail_risk 来源
# ============================================================
def test_tail_risk_from_framework():
    """framework_views 有 tail_risk 组 → tail_risk 维度用它。"""
    fw = [_fw("tail_risk", "bearish", 0.75, 1)]
    rp = build_risk_profile("NFLX", "2026-09-03", {}, fw)
    assert rp.tail_risk.direction == "bearish"
    assert rp.tail_risk.strength == pytest.approx(0.75)


def test_tail_risk_missing_neutral():
    """framework_views 无 tail_risk 组 → tail_risk 回退 neutral。"""
    rp = build_risk_profile("NFLX", "2026-09-03", {}, [])
    assert rp.tail_risk.direction == "neutral"
    assert "no tail_risk framework" in rp.tail_risk.note


# ============================================================
# 5. framework_views 整合
# ============================================================
def test_framework_views_dict_populated():
    fw = [
        _fw("intrinsic_value", "bullish", 0.7, 3),
        _fw("technical", "bearish", 0.6, 1),
    ]
    rp = build_risk_profile("NFLX", "2026-09-03", {}, fw)
    assert len(rp.framework_views) == 2
    assert "intrinsic_value" in rp.framework_views
    assert "technical" in rp.framework_views


# ============================================================
# 6. Rating 边界
# ============================================================
@pytest.mark.parametrize("score,expected", [
    (0.5,  "Buy"),
    (0.3,  "Overweight"),
    (0.0,  "Hold"),
    (-0.3, "Underweight"),
    (-0.5, "Sell"),
])
def test_rating_boundaries(score, expected):
    """验证 _score_to_rating 的边界（通过 build_risk_profile 间接测）。"""
    from valueagents.evidence.risk_profile import _score_to_rating
    assert _score_to_rating(score) == expected


# ============================================================
# 7. confidence 覆盖度
# ============================================================
def test_confidence_increases_with_more_signals():
    """更多信号 → confidence 更高。"""
    eg_small = {"market": _make_bundle([_sig("bullish", 0.8)])}
    eg_large = {"market": _make_bundle([_sig("bullish", 0.8)] * 10)}
    rp_small = build_risk_profile("NFLX", "2026-09-03", eg_small, [])
    rp_large = build_risk_profile("NFLX", "2026-09-03", eg_large, [])
    assert rp_large.confidence >= rp_small.confidence


# ============================================================
# 8. summarize
# ============================================================
def test_summarize_contains_all_dimensions():
    rp = build_risk_profile("NFLX", "2026-09-03", {}, [])
    text = summarize_risk_profile(rp)
    for name in ("trend", "valuation", "tail_risk", "catalyst", "sentiment"):
        assert name in text
    assert "Risk Profile" in text
    assert "Rating" not in text or "rating=" in text  # rating 在 overall 行里


def test_summarize_with_frameworks():
    fw = [_fw("intrinsic_value", "bullish", 0.7, 3)]
    rp = build_risk_profile("NFLX", "2026-09-03", {}, fw)
    text = summarize_risk_profile(rp)
    assert "Framework Views" in text
    assert "intrinsic_value" in text


# ============================================================
# 9. Key claims 去重
# ============================================================
def test_key_claims_deduplicated():
    """同一 claim_id 多次出现 → 去重。"""
    eg = {"market": _make_bundle([
        {"direction": "bullish", "strength": 0.8, "claim_ids": ["cl_a"]},
        {"direction": "bullish", "strength": 0.7, "claim_ids": ["cl_a", "cl_b"]},
    ])}
    rp = build_risk_profile("NFLX", "2026-09-03", eg, [])
    # 去重后只有 2 个
    assert len(rp.trend.key_claims) == 2
    assert set(rp.trend.key_claims) == {"cl_a", "cl_b"}
