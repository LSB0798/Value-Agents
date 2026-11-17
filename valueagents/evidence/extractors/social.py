# ./valueagents/evidence/extractors/social.py
"""Social Media Evidence Extractor — Phase 2 W1.6

framework="sentiment"。social analyst 的 tool 是 get_aggregated_news（1 个）。
"""

from __future__ import annotations

from typing import Any, Optional

from valueagents.evidence.schema import Claim, EvidenceBundle, Signal
from .base import extract_evidence_items


def extract_social_evidence(
    ticker: str,
    end_date: str,
    sentiment_report: str,
    messages: list[Any],
    llm: Optional[Any] = None,
) -> EvidenceBundle:
    """从 social media analyst 的输出提取 EvidenceBundle。"""
    evidence = extract_evidence_items(messages)

    claims: list[Claim] = []
    signals: list[Signal] = []
    version = "w1.0_rule_only"

    if llm is not None and sentiment_report and evidence:
        try:
            from ._llm import extract_claims_and_signals
            claims, signals = extract_claims_and_signals(
                llm=llm,
                ticker=ticker,
                end_date=end_date,
                narrative=sentiment_report,
                evidence=evidence,
                framework="sentiment",
            )
            version = "w1.5_llm"
        except Exception as e:
            print(f"   ⚠️ [social_evidence] LLM extractor failed: {type(e).__name__}: {e}")

    print(
        f"   📦 [social_evidence] version={version} "
        f"evidence={len(evidence)} claims={len(claims)} signals={len(signals)}"
    )

    return EvidenceBundle(
        agent_id="social_analyst",
        ticker=ticker,
        end_date=end_date,
        evidence=evidence,
        claims=claims,
        signals=signals,
        narrative=sentiment_report,
        meta={"extractor_version": version},
    )


__all__ = ["extract_social_evidence"]
