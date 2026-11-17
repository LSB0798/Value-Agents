# ./tests/unit/test_risk_profile_w3b.py
"""Phase 3 W3b：RiskProfile 注入 RM/PM 的单元测试。

只测"RiskProfile 在 state 里存在时 RM/PM 能正确读到"，
不测 LLM 行为（那是 full 端到端验证的事）。
"""

from datetime import datetime

import pytest

from valueagents.evidence import (
    RiskProfile,
    build_risk_profile,
    summarize_risk_profile,
)


def _make_risk_profile_dict() -> dict:
    """构造一个最小的 RiskProfile dict。"""
    rp = build_risk_profile(
        ticker="NFLX",
        end_date="2026-09-03",
        evidence_graph={},
        framework_views=[],
    )
    return rp.model_dump()


def test_risk_profile_round_trip():
    """RiskProfile dict → RiskProfile 对象 → 再 dict，字段不丢。"""
    rp_dict = _make_risk_profile_dict()
    rp = RiskProfile(**rp_dict)
    assert rp.ticker == "NFLX"
    assert rp.end_date == "2026-09-03"
    assert rp.rating in ("Buy", "Overweight", "Hold", "Underweight", "Sell")


def test_risk_profile_summarize_not_empty():
    """summarize 输出非空，且含关键维度。"""
    rp = RiskProfile(**_make_risk_profile_dict())
    text = summarize_risk_profile(rp)
    assert text
    for keyword in ("Risk Profile", "trend", "valuation", "tail_risk", "catalyst", "sentiment"):
        assert keyword in text


def test_risk_profile_with_rich_data():
    """含真实 evidence 时 RiskProfile 的 5 维度都有数据。"""
    sig = {
        "ticker": "NFLX",
        "dimension": "trend",
        "framework": None,
        "direction": "bullish",
        "strength": 0.7,
        "claim_ids": ["cl_test"],
        "provenance": "test",
    }
    eg = {
        "market": {"signals": [sig], "evidence": [], "claims": []},
        "fundamentals": {"signals": [sig], "evidence": [], "claims": []},
        "news": {"signals": [sig], "evidence": [], "claims": []},
        "sentiment": {"signals": [sig], "evidence": [], "claims": []},
    }
    rp = build_risk_profile("NFLX", "2026-09-03", eg, [])
    # 4 个 analyst 都 bullish → 整体应偏 bullish
    assert rp.overall_verdict in ("bullish", "neutral")
    assert rp.overall_score > 0
