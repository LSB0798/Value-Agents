# ./tests/unit/test_social_extractor.py
"""Phase 2 W1.6 social extractor 单元测试。"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import HumanMessage, ToolMessage

from valueagents.evidence.extractors.social import extract_social_evidence


def _tool_msg(name: str, content: str, call_id: str = "c1") -> ToolMessage:
    return ToolMessage(content=content, name=name, tool_call_id=call_id)


def test_empty_messages():
    bundle = extract_social_evidence(
        ticker="NFLX", end_date="2026-09-03",
        sentiment_report="report", messages=[],
    )
    assert bundle.agent_id == "social_analyst"
    assert bundle.evidence == []
    assert bundle.claims == []
    assert bundle.signals == []
    assert bundle.meta["extractor_version"] == "w1.0_rule_only"


def test_evidence_only_without_llm():
    bundle = extract_social_evidence(
        ticker="NFLX", end_date="2026-09-03",
        sentiment_report="report",
        messages=[_tool_msg("get_aggregated_news", "news data")],
    )
    assert len(bundle.evidence) == 1
    assert bundle.claims == []
    assert bundle.meta["extractor_version"] == "w1.0_rule_only"


def test_with_llm_success():
    llm = MagicMock()
    msg = MagicMock()
    msg.content = '{"claims": [{"statement": "Sentiment positive", "confidence": 0.7, "evidence_ids": ["__ID__"]}], "signals": []}'
    llm.invoke.return_value = msg
    # 先跑一次拿真实 evidence id
    b0 = extract_social_evidence(
        ticker="NFLX", end_date="2026-09-03",
        sentiment_report="Sentiment is positive.",
        messages=[_tool_msg("get_aggregated_news", "news data")],
    )
    ev_id = b0.evidence[0].id
    # 用真实 id 重跑
    llm.invoke.return_value.content = (
        f'{{"claims": [{{"statement": "Sentiment positive", "confidence": 0.7, '
        f'"evidence_ids": ["{ev_id}"], "framework": "sentiment"}}], "signals": []}}'
    )
    bundle = extract_social_evidence(
        ticker="NFLX", end_date="2026-09-03",
        sentiment_report="Sentiment is positive.",
        messages=[_tool_msg("get_aggregated_news", "news data")],
        llm=llm,
    )
    assert len(bundle.claims) == 1
    assert bundle.meta["extractor_version"] == "w1.5_llm"


def test_llm_failure_fallback():
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("LLM down")
    bundle = extract_social_evidence(
        ticker="NFLX", end_date="2026-09-03",
        sentiment_report="report",
        messages=[_tool_msg("get_aggregated_news", "news")],
        llm=llm,
    )
    assert bundle.claims == []
    assert bundle.signals == []
    assert bundle.meta["extractor_version"] == "w1.5_llm"


def test_skip_non_tool_messages():
    bundle = extract_social_evidence(
        ticker="NFLX", end_date="2026-09-03",
        sentiment_report="report",
        messages=[HumanMessage(content="hi"), _tool_msg("get_aggregated_news", "news")],
    )
    assert len(bundle.evidence) == 1
