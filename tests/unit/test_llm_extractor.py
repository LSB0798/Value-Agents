# ./tests/unit/test_llm_extractor.py
"""Phase 2 W1.5 LLM 提取器单元测试（mock LLM）。"""

from unittest.mock import MagicMock
from datetime import datetime

from valueagents.evidence.schema import EvidenceItem
from valueagents.evidence.extractors._llm import extract_claims_and_signals


def _ev(ev_id: str = "ev_rsi"):
    return EvidenceItem(
        id=ev_id, source="get_indicators:rsi", source_type="agent",
        timestamp=datetime(2026, 9, 3),
        content={"text": "rsi=72.5"}, raw_ref="tool_result",
    )


def _mock_llm(json_content: str):
    llm = MagicMock()
    msg = MagicMock()
    msg.content = json_content
    llm.invoke.return_value = msg
    return llm


def test_valid_extraction_claims_only():
    """只有 claims 时，signals 为空是合法的。"""
    llm = _mock_llm("""
    {"claims": [
        {"statement": "RSI overbought", "confidence": 0.8,
         "evidence_ids": ["ev_rsi"], "framework": "technical"}
    ], "signals": []}
    """)
    claims, signals = extract_claims_and_signals(
        llm=llm, ticker="NFLX", end_date="2026-09-03",
        narrative="RSI at 72.5 suggests overbought.", evidence=[_ev()],
    )
    assert len(claims) == 1
    assert claims[0].statement == "RSI overbought"
    assert claims[0].evidence_ids == ["ev_rsi"]
    assert signals == []


def test_valid_extraction_with_signal_via_refs():
    """claim_refs=C1 → 映射到真实 claim id。"""
    llm = _mock_llm("""
    {
      "claims": [
        {"statement": "RSI overbought", "confidence": 0.8,
         "evidence_ids": ["ev_rsi"], "framework": "technical"}
      ],
      "signals": [
        {"dimension": "trend", "direction": "bearish", "strength": 0.7,
         "claim_refs": ["C1"], "framework": "technical",
         "provenance": "1 technical claim"}
      ]
    }
    """)
    claims, signals = extract_claims_and_signals(
        llm=llm, ticker="NFLX", end_date="2026-09-03",
        narrative="RSI at 72.5", evidence=[_ev()],
    )
    assert len(claims) == 1
    assert len(signals) == 1
    sig = signals[0]
    assert sig.direction == "bearish"
    assert sig.claim_ids == [claims[0].id]   # 关键：映射到了真实 hash
    assert sig.ticker == "NFLX"


def test_multiple_claims_multiple_signals():
    llm = _mock_llm("""
    {
      "claims": [
        {"statement": "A", "confidence": 0.9, "evidence_ids": ["ev_rsi"], "framework": "technical"},
        {"statement": "B", "confidence": 0.8, "evidence_ids": ["ev_rsi"], "framework": "technical"},
        {"statement": "C", "confidence": 0.7, "evidence_ids": ["ev_rsi"], "framework": "technical"}
      ],
      "signals": [
        {"dimension": "trend", "direction": "bearish", "strength": 0.8,
         "claim_refs": ["C1", "C2"], "framework": "technical", "provenance": "..."},
        {"dimension": "momentum", "direction": "neutral", "strength": 0.5,
         "claim_refs": ["C3"], "framework": "technical", "provenance": "..."}
      ]
    }
    """)
    claims, signals = extract_claims_and_signals(
        llm=llm, ticker="NFLX", end_date="2026-09-03",
        narrative="...", evidence=[_ev()],
    )
    assert len(claims) == 3
    assert len(signals) == 2
    assert set(signals[0].claim_ids) == {claims[0].id, claims[1].id}
    assert signals[1].claim_ids == [claims[2].id]


def test_hallucinated_evidence_id_dropped():
    llm = _mock_llm("""
    {"claims": [
        {"statement": "Made up", "confidence": 0.9,
         "evidence_ids": ["ev_nonexistent"], "framework": "technical"}
    ], "signals": []}
    """)
    claims, signals = extract_claims_and_signals(
        llm=llm, ticker="NFLX", end_date="2026-09-03",
        narrative="...", evidence=[_ev()],
    )
    assert claims == []
    assert signals == []


def test_hallucinated_claim_refs_dropped():
    """claim_refs 引用不存在的 C 编号 → 该 signal 被丢弃。"""
    llm = _mock_llm("""
    {
      "claims": [
        {"statement": "A", "confidence": 0.8, "evidence_ids": ["ev_rsi"], "framework": "technical"}
      ],
      "signals": [
        {"dimension": "trend", "direction": "bearish", "strength": 0.7,
         "claim_refs": ["C99"], "framework": "technical", "provenance": "..."}
      ]
    }
    """)
    claims, signals = extract_claims_and_signals(
        llm=llm, ticker="NFLX", end_date="2026-09-03",
        narrative="...", evidence=[_ev()],
    )
    assert len(claims) == 1
    assert signals == []   # 被丢弃


def test_empty_narrative_returns_empty():
    llm = _mock_llm("{}")
    claims, signals = extract_claims_and_signals(
        llm=llm, ticker="NFLX", end_date="2026-09-03",
        narrative="", evidence=[_ev()],
    )
    assert claims == [] and signals == []


def test_llm_failure_returns_empty():
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("LLM down")
    claims, signals = extract_claims_and_signals(
        llm=llm, ticker="NFLX", end_date="2026-09-03",
        narrative="text", evidence=[_ev()],
    )
    assert claims == [] and signals == []


def test_unparseable_output_returns_empty():
    llm = _mock_llm("this is not JSON")
    claims, signals = extract_claims_and_signals(
        llm=llm, ticker="NFLX", end_date="2026-09-03",
        narrative="text", evidence=[_ev()],
    )
    assert claims == [] and signals == []
