# ./tests/unit/test_fundamentals_extractor.py
"""Phase 2 W1.6 fundamentals extractor 单元测试。"""

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import ToolMessage

from valueagents.evidence.extractors.fundamentals import extract_fundamentals_evidence


def _tool_msg(name: str, content: str, call_id: str = "c1") -> ToolMessage:
    return ToolMessage(content=content, name=name, tool_call_id=call_id)


def test_empty_messages():
    bundle = extract_fundamentals_evidence(
        ticker="NFLX", end_date="2026-09-03",
        fundamentals_report="report", messages=[],
    )
    assert bundle.agent_id == "fundamentals_analyst"
    assert bundle.meta["extractor_version"] == "w1.0_rule_only"


def test_four_tools_evidence():
    """fundamentals analyst 有 4 个 tool，应提取出 4 个 evidence。"""
    bundle = extract_fundamentals_evidence(
        ticker="NFLX", end_date="2026-09-03",
        fundamentals_report="report",
        messages=[
            _tool_msg("get_fundamentals", "overview", "c1"),
            _tool_msg("get_balance_sheet", "bs", "c2"),
            _tool_msg("get_cashflow", "cf", "c3"),
            _tool_msg("get_income_statement", "is", "c4"),
        ],
    )
    assert len(bundle.evidence) == 4


def test_with_llm():
    llm = MagicMock()
    msg = MagicMock()
    llm.invoke.return_value = msg

    b0 = extract_fundamentals_evidence(
        ticker="NFLX", end_date="2026-09-03",
        fundamentals_report="fundamentals text",
        messages=[_tool_msg("get_fundamentals", "data")],
    )
    ev_id = b0.evidence[0].id

    msg.content = (
        f'{{"claims": [{{"statement": "Strong margins", "confidence": 0.8, '
        f'"evidence_ids": ["{ev_id}"], "framework": "fundamental"}}], "signals": []}}'
    )
    bundle = extract_fundamentals_evidence(
        ticker="NFLX", end_date="2026-09-03",
        fundamentals_report="fundamentals text",
        messages=[_tool_msg("get_fundamentals", "data")],
        llm=llm,
    )
    assert len(bundle.claims) == 1
    assert bundle.meta["extractor_version"] == "w1.5_llm"


def test_llm_failure_fallback():
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("fail")
    bundle = extract_fundamentals_evidence(
        ticker="NFLX", end_date="2026-09-03",
        fundamentals_report="report",
        messages=[_tool_msg("get_fundamentals", "data")],
        llm=llm,
    )
    # LLM 尝试了但失败 → version=w1.5_llm，但 claims/signals 为空
    assert bundle.claims == []
    assert bundle.signals == []
    assert bundle.meta["extractor_version"] == "w1.5_llm"
