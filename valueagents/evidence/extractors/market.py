# ./valueagents/evidence/extractors/market.py
"""Market Evidence Extractor — Phase 2 W1.5

两阶段提取：
  W1.0（规则）：每个 ToolMessage → 1 个 EvidenceItem
  W1.5（LLM） ：从 narrative 提取 3-8 个 Claim + 1-3 个 Signal

向后兼容：
  - llm=None 时退化为 W1.0 纯规则（claims/signals 为空）
  - LLM 失败时返回空 claims/signals，bundle 仍然合法
"""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.messages import ToolMessage

from valueagents.evidence.schema import Claim, EvidenceBundle, EvidenceItem, Signal
from .base import make_evidence_id, now_utc


_MAX_TOOL_TEXT = 2000  # 单个 tool 结果在 evidence.content 里的截断长度


# ============================================================
# W1.0：规则提取（ToolMessage → EvidenceItem）
# ============================================================
def _extract_evidence_from_messages(
    messages: list[Any],
) -> list[EvidenceItem]:
    """遍历 messages，把每个 ToolMessage 转成 1 个 EvidenceItem。"""
    evidence: list[EvidenceItem] = []

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue

        raw_content = msg.content if msg.content is not None else ""
        if not raw_content:
            continue

        tool_name = getattr(msg, "name", None) or "tool"
        tool_call_id = getattr(msg, "tool_call_id", None) or "unknown"

        content_str = str(raw_content)
        preview = content_str[:_MAX_TOOL_TEXT]

        ev_id = make_evidence_id(tool_name, preview)
        evidence.append(
            EvidenceItem(
                id=ev_id,
                source=f"tool:{tool_name}",
                source_type="external",
                timestamp=now_utc(),
                content={
                    "text": preview,
                    "full_length": len(content_str),
                    "truncated": len(content_str) > _MAX_TOOL_TEXT,
                },
                raw_ref=f"tool_call:{tool_call_id}",
            )
        )

    return evidence


# ============================================================
# W1.5：LLM 提取（narrative + evidence → claims + signals）
# ============================================================
def _extract_claims_and_signals(
    llm: Any,
    ticker: str,
    end_date: str,
    narrative: str,
    evidence: list[EvidenceItem],
    framework: str = "technical",
) -> tuple[list[Claim], list[Signal]]:
    """调 LLM 提取 claim/signal，失败返回空。

    延迟 import `_llm`，避免 W1.0 用户（llm=None）加载额外依赖。
    """
    try:
        from ._llm import extract_claims_and_signals
    except ImportError as e:
        print(f"   ⚠️ [market_evidence] _llm.py not available: {e}")
        return [], []

    return extract_claims_and_signals(
        llm=llm,
        ticker=ticker,
        end_date=end_date,
        narrative=narrative,
        evidence=evidence,
        framework=framework,
    )


# ============================================================
# 主入口
# ============================================================
def extract_market_evidence(
    ticker: str,
    end_date: str,
    market_report: str,
    messages: list[Any],
    llm: Optional[Any] = None,
) -> EvidenceBundle:
    """从 market analyst 的输出提取 EvidenceBundle。

    Args:
        ticker: 股票代码
        end_date: YYYY-MM-DD
        market_report: LLM 生成的 Markdown 报告（作为 narrative 保留）
        messages: state["messages"] 列表（含 ToolMessage）
        llm: 可选的 LangChain LLM 实例。传入时走 W1.5（LLM 提取 claim/signal）；
             为 None 时退化为 W1.0（纯规则，claims/signals 为空）。

    Returns:
        EvidenceBundle：
        - evidence: 每个 ToolMessage 1 个，共 N 个
        - claims: W1.5 且 LLM 成功时 3-8 个；否则 []
        - signals: W1.5 且 LLM 成功时 1-3 个；否则 []
        - narrative: market_report 原样
        - meta: extractor_version ("w1.0_rule_only" / "w1.5_llm")
    """
    # ---------- 阶段 1：规则提取（必有） ----------
    evidence = _extract_evidence_from_messages(messages)

    # ---------- 阶段 2：LLM 提取（可选） ----------
    claims: list[Claim] = []
    signals: list[Signal] = []
    version = "w1.0_rule_only"

    if llm is not None and market_report and evidence:
        claims, signals = _extract_claims_and_signals(
            llm=llm,
            ticker=ticker,
            end_date=end_date,
            narrative=market_report,
            evidence=evidence,
            framework="technical",
        )
        version = "w1.5_llm"

    # ---------- 组装 ----------
    print(
        f"   📦 [market_evidence] version={version} "
        f"evidence={len(evidence)} claims={len(claims)} signals={len(signals)}"
    )

    return EvidenceBundle(
        agent_id="market_analyst",
        ticker=ticker,
        end_date=end_date,
        evidence=evidence,
        claims=claims,
        signals=signals,
        narrative=market_report,
        meta={"extractor_version": version},
    )


__all__ = ["extract_market_evidence"]