# ./tests/unit/test_evidence_graph.py
"""Phase 1 F1.2 单元测试。"""

import pytest
from datetime import datetime

from valueagents.evidence import (
    Claim, EvidenceBundle, EvidenceGraph, EvidenceItem, Signal,
)


def _make_bundle(agent_id="market_analyst"):
    return EvidenceBundle(
        agent_id=agent_id, ticker="NFLX", end_date="2026-09-03",
        evidence=[EvidenceItem(
            id=f"ev_{agent_id}_rsi", source="get_indicators:rsi",
            source_type="agent", timestamp=datetime(2026, 9, 3),
            content={"rsi": 72.5}, raw_ref="tool_result:get_indicators",
        )],
        claims=[Claim(
            id=f"cl_{agent_id}_overbought", statement="RSI overbought",
            confidence=0.8, evidence_ids=[f"ev_{agent_id}_rsi"],
            framework="technical",
        )],
        signals=[Signal(
            ticker="NFLX", dimension="trend", framework=None,
            direction="bearish", strength=0.7,
            claim_ids=[f"cl_{agent_id}_overbought"],
            provenance="aggregated",
        )],
        narrative="mock narrative",
    )


def test_add_bundle():
    g = EvidenceGraph("NFLX", "2026-09-03")
    g.add_bundle(_make_bundle())
    assert g.keys()["evidence"] == 1
    assert g.keys()["claims"] == 1
    assert g.keys()["signals"] == 1


def test_add_bundle_ticker_mismatch():
    g = EvidenceGraph("NFLX", "2026-09-03")
    with pytest.raises(ValueError, match="ticker mismatch"):
        b = _make_bundle(); b.ticker = "GOOGL"
        g.add_bundle(b)


def test_add_two_bundles_merge():
    g = EvidenceGraph("NFLX", "2026-09-03")
    g.add_bundle(_make_bundle("market_analyst"))
    g.add_bundle(_make_bundle("news_analyst"))
    assert g.keys()["agents"] == 2
    assert g.keys()["signals"] == 2


def test_view_full():
    g = EvidenceGraph("NFLX", "2026-09-03")
    g.add_bundle(_make_bundle())
    text = g.to_view("full", max_chars=5000)
    assert "## Evidence" in text
    assert "## Claims" in text
    assert "## Signals" in text


def test_view_claims():
    g = EvidenceGraph("NFLX", "2026-09-03")
    g.add_bundle(_make_bundle())
    text = g.to_view("claims")
    assert "cl_market_analyst_overbought" in text
    assert "technical" in text


def test_view_signals():
    g = EvidenceGraph("NFLX", "2026-09-03")
    g.add_bundle(_make_bundle())
    text = g.to_view("signals")
    assert "trend" in text
    assert "bearish" in text
    assert "strength=0.70" in text


def test_view_compact():
    g = EvidenceGraph("NFLX", "2026-09-03")
    g.add_bundle(_make_bundle())
    text = g.to_view("compact")
    assert "bearish" in text
    assert "n=1" in text


def test_view_empty_graph():
    g = EvidenceGraph("NFLX", "2026-09-03")
    for view in ["full", "claims", "signals", "compact"]:
        assert g.to_view(view) == "(empty evidence graph)"


def test_view_truncation():
    g = EvidenceGraph("NFLX", "2026-09-03")
    g.add_bundle(_make_bundle())
    text = g.to_view("full", max_chars=100)
    assert len(text) <= 100
    assert text.endswith("...")


def test_unknown_view():
    g = EvidenceGraph("NFLX", "2026-09-03")
    with pytest.raises(ValueError, match="Unknown view"):
        g.to_view("invalid_view")


def test_filter_by_framework():
    g = EvidenceGraph("NFLX", "2026-09-03")
    g.add_bundle(_make_bundle())
    text = g.to_view("claims", filter={"framework": "technical"})
    assert "overbought" in text.lower()
    text = g.to_view("claims", filter={"framework": "macro"})
    assert text == "(no claims matched)"


def test_filter_by_min_confidence():
    g = EvidenceGraph("NFLX", "2026-09-03")
    g.add_bundle(_make_bundle())
    text = g.to_view("claims", filter={"min_confidence": 0.9})
    assert text == "(no claims matched)"
    text = g.to_view("claims", filter={"min_confidence": 0.5})
    assert "overbought" in text.lower()


def test_filter_by_dimension():
    g = EvidenceGraph("NFLX", "2026-09-03")
    g.add_bundle(_make_bundle())
    text = g.to_view("signals", filter={"dimension": "trend"})
    assert "trend" in text
    text = g.to_view("signals", filter={"dimension": "valuation"})
    assert text == "(no signals matched)"


def test_to_dict_round_trip():
    g = EvidenceGraph("NFLX", "2026-09-03")
    g.add_bundle(_make_bundle())
    d = g.to_dict()
    g2 = EvidenceGraph.from_dict(d)
    assert g2.keys() == g.keys()
    assert g2.ticker == g.ticker
