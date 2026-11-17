# ./tests/unit/test_news_extractor.py
"""Phase 2 W1.6 news extractor 单元测试。"""

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import ToolMessage

from valueagents.evidence.extractors.news import extract_news_evidence


def _tool_msg(name: str, content: str, call_id: str = "c1") -> ToolMessage:
    return ToolMessage(content=content, name=name, tool_call_id=call_id)


def test_empty_messages():
    """不传 llm + messages 空 → 没尝试 LLM → w1.0_rule_only。"""
    bundle = extract_news_evidence(
        ticker="NFLX", end_date="2026-09-03",
        news_report="report", messages=[],
    )
    assert bundle.agent_id == "news_analyst"
    assert bundle.evidence == []
    assert bundle.claims == []
    assert bundle.signals == []
    assert bundle.meta["extractor_version"] == "w1.0_rule_only"   # ✅ 正确


def test_two_tools_evidence():
    """news analyst 有 2 个 tool，应提取出 2 个 evidence。"""
    bundle = extract_news_evidence(
        ticker="NFLX", end_date="2026-09-03",
        news_report="report",
        messages=[
            _tool_msg("get_aggregated_news", "company news", "c1"),
            _tool_msg("get_aggregated_global_news", "macro news", "c2"),
        ],
    )
    assert len(bundle.evidence) == 2
    # 不传 llm → 没尝试 LLM
    assert bundle.meta["extractor_version"] == "w1.0_rule_only"


def test_with_llm():
    """传 llm 且成功 → w1.5_llm + claims 非空。"""
    llm = MagicMock()
    msg = MagicMock()
    llm.invoke.return_value = msg

    b0 = extract_news_evidence(
        ticker="NFLX", end_date="2026-09-03",
        news_report="news text",
        messages=[_tool_msg("get_aggregated_news", "data")],
    )
    ev_id = b0.evidence[0].id

    msg.content = (
        f'{{"claims": [{{"statement": "Macro tailwind", "confidence": 0.6, '
        f'"evidence_ids": ["{ev_id}"], "framework": "news"}}], "signals": []}}'
    )
    bundle = extract_news_evidence(
        ticker="NFLX", end_date="2026-09-03",
        news_report="news text",
        messages=[_tool_msg("get_aggregated_news", "data")],
        llm=llm,
    )
    assert len(bundle.claims) == 1
    assert bundle.meta["extractor_version"] == "w1.5_llm"


def test_llm_failure_fallback():
    """传 llm 且抛异常 → 尝试了 LLM（version=w1.5_llm），但 claims/signals 为空。"""
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("fail")
    bundle = extract_news_evidence(
        ticker="NFLX", end_date="2026-09-03",
        news_report="report",
        messages=[_tool_msg("get_aggregated_news", "data")],
        llm=llm,
    )
    assert bundle.claims == []
    assert bundle.signals == []
    assert bundle.meta["extractor_version"] == "w1.5_llm"
