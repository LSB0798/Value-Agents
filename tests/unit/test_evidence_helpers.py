# ./tests/unit/test_evidence_helpers.py
"""Phase 2 W2.0 helpers 单元测试。"""

from datetime import datetime

import pytest

from valueagents.evidence import (
    Claim,
    EvidenceBundle,
    EvidenceItem,
    Signal,
)
from valueagents.evidence.helpers import get_evidence_view, get_hybrid_view


def _make_artifacts(with_evidence: bool = True) -> dict:
    """构造测试用 artifacts（模拟 LangGraph state）。"""
    report = "# NFLX Analysis\n\n" + ("Lorem ipsum. " * 500)  # 6000+ chars

    artifacts = {
        "market_report": report,
        "sentiment_report": "# Sentiment\n\n" + ("Sent. " * 300),
        "news_report": "# News\n\n" + ("News. " * 300),
        "fundamentals_report": "# Fundamentals\n\n" + ("Fund. " * 500),
    }

    if with_evidence:
        bundle = EvidenceBundle(
            agent_id="market_analyst",
            ticker="NFLX",
            end_date="2026-09-03",
            evidence=[EvidenceItem(
                id="ev_rsi", source="get_indicators:rsi", source_type="agent",
                timestamp=datetime(2026, 9, 3),
                content={"text": "rsi=72.5"}, raw_ref="tool_result",
            )],
            claims=[Claim(
                id="cl_overbought", statement="RSI is overbought",
                confidence=0.8, evidence_ids=["ev_rsi"], framework="technical",
            )],
            signals=[Signal(
                ticker="NFLX", dimension="trend", framework=None,
                direction="bearish", strength=0.7,
                claim_ids=["cl_overbought"], provenance="1 claim",
            )],
            narrative=report,
        )
        artifacts["market_evidence"] = bundle.model_dump()

    return artifacts


# ============================================================
# get_evidence_view
# ============================================================
def test_evidence_view_with_evidence():
    """有 evidence → 返回 claims view。"""
    artifacts = _make_artifacts(with_evidence=True)
    text = get_evidence_view(artifacts, "market", view="claims")
    assert "cl_overbought" in text
    assert "overbought" in text.lower()


def test_evidence_view_without_evidence():
    """无 evidence → fallback 到 narrative 截断。"""
    artifacts = _make_artifacts(with_evidence=False)
    text = get_evidence_view(artifacts, "market", max_chars=1000)
    assert len(text) <= 1000
    assert "# NFLX Analysis" in text


def test_evidence_view_truncation():
    """输出长度 ≤ max_chars。"""
    artifacts = _make_artifacts(with_evidence=True)
    text = get_evidence_view(artifacts, "market", max_chars=100)
    assert len(text) <= 100


# ============================================================
# get_hybrid_view
# ============================================================
def test_hybrid_view_contains_both():
    """hybrid 同时含 evidence 和 narrative。"""
    artifacts = _make_artifacts(with_evidence=True)
    text = get_hybrid_view(artifacts, "market", max_chars=4000)
    assert "## Structured Evidence" in text
    assert "## Full Report" in text
    assert "overbought" in text.lower()  # evidence 内容
    assert "Lorem ipsum" in text         # narrative 内容


def test_hybrid_view_truncation():
    """hybrid 输出 ≤ max_chars。"""
    artifacts = _make_artifacts(with_evidence=True)
    text = get_hybrid_view(artifacts, "market", max_chars=500)
    assert len(text) <= 500


def test_hybrid_view_without_evidence_fallback():
    """无 evidence → 纯 narrative 截断。"""
    artifacts = _make_artifacts(with_evidence=False)
    text = get_hybrid_view(artifacts, "market", max_chars=1000)
    assert "## Structured Evidence" not in text
    assert len(text) <= 1000
    assert "# NFLX Analysis" in text


def test_hybrid_view_empty_report():
    """空 narrative + 无 evidence → 空字符串（不崩）。"""
    artifacts = {"market_report": ""}
    text = get_hybrid_view(artifacts, "market")
    assert text == ""


def test_hybrid_view_evidence_ratio():
    """evidence_ratio 控制 evidence 部分占比。"""
    artifacts = _make_artifacts(with_evidence=True)
    # 低 ratio → evidence 部分更短
    low_ratio = get_hybrid_view(artifacts, "market", max_chars=2000, evidence_ratio=0.2)
    high_ratio = get_hybrid_view(artifacts, "market", max_chars=2000, evidence_ratio=0.5)
    # 两者都有 evidence 和 narrative，但 evidence 部分长度不同
    assert len(low_ratio) <= 2000
    assert len(high_ratio) <= 2000
