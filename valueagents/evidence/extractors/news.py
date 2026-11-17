# ./valueagents/evidence/extractors/news.py
"""News Evidence Extractor — Phase 2 W1.6

framework="news"。news analyst 的 tool 是 get_aggregated_news + get_aggregated_global_news（2 个）。
"""

from __future__ import annotations

from typing import Any, Optional

from valueagents.evidence.schema import Claim, EvidenceBundle, Signal
from .base import extract_evidence_items


def extract_news_evidence(
    ticker: str,
    end_date: str,
    news_report: str,
    messages: list[Any],
    llm: Optional[Any] = None,
) -> EvidenceBundle:
    """从 news analyst 的输出提取 EvidenceBundle。"""
    evidence = extract_evidence_items(messages)

    claims: list[Claim] = []
    signals: list[Signal] = []
    version = "w1.0_rule_only"

    if llm is not None and news_report and evidence:
        try:
            from ._llm import extract_claims_and_signals
            claims, signals = extract_claims_and_signals(
                llm=llm,
                ticker=ticker,
                end_date=end_date,
                narrative=news_report,
                evidence=evidence,
                framework="news",
            )
            version = "w1.5_llm"
        except Exception as e:
            print(f"   ⚠️ [news_evidence] LLM extractor failed: {type(e).__name__}: {e}")

    print(
        f"   📦 [news_evidence] version={version} "
        f"evidence={len(evidence)} claims={len(claims)} signals={len(signals)}"
    )

    return EvidenceBundle(
        agent_id="news_analyst",
        ticker=ticker,
        end_date=end_date,
        evidence=evidence,
        claims=claims,
        signals=signals,
        narrative=news_report,
        meta={"extractor_version": version},
    )


__all__ = ["extract_news_evidence"]
