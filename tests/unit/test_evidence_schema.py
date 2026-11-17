# ./tests/unit/test_evidence_schema.py
"""Phase 1 F1.1 单元测试。"""

import pytest
from datetime import datetime

from valueagents.evidence import (
    Claim, EvidenceBundle, EvidenceItem, Signal,
)


def _ev(ev_id="ev_rsi"):
    return EvidenceItem(
        id=ev_id, source="get_indicators:rsi", source_type="agent",
        timestamp=datetime(2026, 9, 3),
        content={"rsi": 72.5, "period": 14},
        raw_ref="tool_result:get_indicators(NFLX, rsi, 2026-09-03)",
    )


def _cl(cl_id="cl_overbought", evidence_ids=None):
    return Claim(
        id=cl_id, statement="RSI 72.5 indicates overbought",
        confidence=0.8, evidence_ids=evidence_ids or ["ev_rsi"],
        framework="technical",
    )


def _sig(claim_ids=None, dimension="trend"):
    return Signal(
        ticker="NFLX", dimension=dimension, framework=None,
        direction="bearish", strength=0.7,
        claim_ids=claim_ids or ["cl_overbought"],
        provenance="aggregated from 1 technical claim",
    )


def test_valid_bundle():
    b = EvidenceBundle(
        agent_id="market_analyst", ticker="NFLX", end_date="2026-09-03",
        evidence=[_ev()], claims=[_cl()], signals=[_sig()],
        narrative="# NFLX Analysis",
    )
    assert len(b.evidence) == 1 and len(b.claims) == 1 and len(b.signals) == 1


def test_missing_evidence_in_claim():
    with pytest.raises(ValueError, match="references missing evidence"):
        EvidenceBundle(
            agent_id="x", ticker="NFLX", end_date="2026-09-03",
            evidence=[], claims=[_cl(evidence_ids=["ev_rsi"])], signals=[],
        )


def test_missing_claim_in_signal():
    with pytest.raises(ValueError, match="references missing claims"):
        EvidenceBundle(
            agent_id="x", ticker="NFLX", end_date="2026-09-03",
            evidence=[_ev()], claims=[], signals=[_sig()],
        )


def test_empty_evidence_ids():
    with pytest.raises(Exception):
        Claim(id="cl_x", statement="x", confidence=0.5,
              evidence_ids=[], framework="technical")


def test_empty_claim_ids():
    with pytest.raises(Exception):
        Signal(ticker="NFLX", dimension="trend", direction="neutral",
               strength=0.5, claim_ids=[], provenance="x")


def test_invalid_evidence_id_pattern():
    with pytest.raises(Exception):
        _ev(ev_id="bad_id")


def test_invalid_claim_id_pattern():
    with pytest.raises(Exception):
        _cl(cl_id="bad_cl")


def test_invalid_confidence_range():
    with pytest.raises(Exception):
        Claim(id="cl_x", statement="x", confidence=1.5,
              evidence_ids=["ev_rsi"], framework="technical")


def test_invalid_direction():
    with pytest.raises(Exception):
        Signal(ticker="NFLX", dimension="trend", direction="maybe",
               strength=0.5, claim_ids=["cl_overbought"], provenance="x")


def test_invalid_end_date():
    with pytest.raises(Exception):
        EvidenceBundle(agent_id="x", ticker="NFLX", end_date="2026/09/03",
                       evidence=[], claims=[], signals=[])


def test_custom_dimension_allowed():
    sig = Signal(ticker="NFLX", dimension="my_custom_dim",
                 direction="neutral", strength=0.5,
                 claim_ids=["cl_overbought"], provenance="x")
    assert sig.dimension == "my_custom_dim"


def test_framework_optional():
    sig = Signal(ticker="NFLX", dimension="trend", direction="neutral",
                 strength=0.5, claim_ids=["cl_overbought"], provenance="x")
    assert sig.framework is None
