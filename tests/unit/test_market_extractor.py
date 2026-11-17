# ./tests/unit/test_market_extractor.py
"""Phase 2 W1.0 提取器单元测试。"""

from datetime import datetime

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from valueagents.evidence.extractors.market import extract_market_evidence


def _tool_msg(name: str, content: str, tool_call_id: str = "call_123"):
    return ToolMessage(content=content, name=name, tool_call_id=tool_call_id)


def test_empty_messages():
    """空 messages → 空 evidence，但 bundle 合法。"""
    bundle = extract_market_evidence(
        ticker="NFLX",
        end_date="2026-09-03",
        market_report="some report",
        messages=[],
    )
    assert bundle.agent_id == "market_analyst"
    assert bundle.evidence == []
    assert bundle.claims == []
    assert bundle.signals == []
    assert bundle.narrative == "some report"


def test_single_tool_message():
    """1 个 ToolMessage → 1 个 EvidenceItem。"""
    bundle = extract_market_evidence(
        ticker="NFLX",
        end_date="2026-09-03",
        market_report="report",
        messages=[
            HumanMessage(content="NFLX"),
            _tool_msg("get_stock_data", "Date,Close\n2026-09-02,82.73\n2026-09-01,80.5"),
            AIMessage(content="based on data..."),
        ],
    )
    assert len(bundle.evidence) == 1
    ev = bundle.evidence[0]
    assert ev.id.startswith("ev_")
    assert "get_stock_data" in ev.source
    assert ev.source_type == "external"
    assert "82.73" in ev.content["text"]
    assert ev.raw_ref == "tool_call:call_123"


def test_multiple_tool_messages():
    """多个 ToolMessage → 多个 EvidenceItem，ID 不冲突。"""
    bundle = extract_market_evidence(
        ticker="NFLX",
        end_date="2026-09-03",
        market_report="report",
        messages=[
            _tool_msg("get_stock_data", "data A", "call_1"),
            _tool_msg("get_indicators", "rsi=72.5", "call_2"),
            _tool_msg("get_indicators", "macd=1.2", "call_3"),
        ],
    )
    assert len(bundle.evidence) == 3
    ids = {ev.id for ev in bundle.evidence}
    assert len(ids) == 3, "evidence IDs 应互不相同"


def test_skip_non_tool_messages():
    """HumanMessage / AIMessage 被跳过。"""
    bundle = extract_market_evidence(
        ticker="NFLX",
        end_date="2026-09-03",
        market_report="report",
        messages=[
            HumanMessage(content="hi"),
            AIMessage(content="hello"),
            _tool_msg("get_stock_data", "data"),
        ],
    )
    assert len(bundle.evidence) == 1


def test_skip_empty_tool_content():
    """空的 tool 返回被跳过。"""
    bundle = extract_market_evidence(
        ticker="NFLX",
        end_date="2026-09-03",
        market_report="report",
        messages=[
            _tool_msg("tool_a", ""),
            _tool_msg("tool_b", "real data"),
        ],
    )
    assert len(bundle.evidence) == 1


def test_truncate_long_tool_content():
    """超长 tool 内容截断到 2000 字，但记录 full_length。"""
    long_content = "x" * 5000
    bundle = extract_market_evidence(
        ticker="NFLX",
        end_date="2026-09-03",
        market_report="report",
        messages=[_tool_msg("tool_a", long_content)],
    )
    assert len(bundle.evidence) == 1
    ev = bundle.evidence[0]
    assert len(ev.content["text"]) == 2000
    assert ev.content["full_length"] == 5000
    assert ev.content["truncated"] is True


def test_short_content_not_truncated():
    bundle = extract_market_evidence(
        ticker="NFLX",
        end_date="2026-09-03",
        market_report="report",
        messages=[_tool_msg("tool_a", "short")],
    )
    ev = bundle.evidence[0]
    assert ev.content["truncated"] is False
    assert ev.content["full_length"] == 5


def test_narrative_preserved():
    """narrative 原样保留。"""
    report = "# NFLX Analysis\n\nStrong buy signal..."
    bundle = extract_market_evidence(
        ticker="NFLX",
        end_date="2026-09-03",
        market_report=report,
        messages=[],
    )
    assert bundle.narrative == report


def test_bundle_is_valid():
    """产物能通过 EvidenceBundle 三层 validator。"""
    bundle = extract_market_evidence(
        ticker="NFLX",
        end_date="2026-09-03",
        market_report="report",
        messages=[_tool_msg("get_stock_data", "data")],
    )
    # model_dump 能正常序列化
    d = bundle.model_dump()
    assert d["agent_id"] == "market_analyst"
    assert len(d["evidence"]) == 1
    # 能重建（round-trip）
    from valueagents.evidence.schema import EvidenceBundle
    bundle2 = EvidenceBundle(**d)
    assert bundle2.agent_id == bundle.agent_id
