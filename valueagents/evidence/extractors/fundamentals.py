# ./valueagents/evidence/extractors/fundamentals.py
"""Fundamentals Evidence Extractor — Phase 2 W1.6

framework="fundamental"。fundamentals analyst 的 tool 有 4 个：
get_fundamentals / get_balance_sheet / get_cashflow / get_income_statement
"""

from __future__ import annotations

from typing import Any, Optional

from valueagents.evidence.schema import Claim, EvidenceBundle, Signal
from .base import extract_evidence_items


def extract_fundamentals_evidence(
    ticker: str,
    end_date: str,
    fundamentals_report: str,
    messages: list[Any],
    llm: Optional[Any] = None,
) -> EvidenceBundle:
    """从 fundamentals analyst 的输出提取 EvidenceBundle。"""
    evidence = extract_evidence_items(messages)

    claims: list[Claim] = []
    signals: list[Signal] = []
    version = "w1.0_rule_only"

    if llm is not None and fundamentals_report and evidence:
        try:
            from ._llm import extract_claims_and_signals
            claims, signals = extract_claims_and_signals(
                llm=llm,
                ticker=ticker,
                end_date=end_date,
                narrative=fundamentals_report,
                evidence=evidence,
                framework="fundamental",
            )
            version = "w1.5_llm"
        except Exception as e:
            print(f"   ⚠️ [fundamentals_evidence] LLM extractor failed: {type(e).__name__}: {e}")

    print(
        f"   📦 [fundamentals_evidence] version={version} "
        f"evidence={len(evidence)} claims={len(claims)} signals={len(signals)}"
    )

    return EvidenceBundle(
        agent_id="fundamentals_analyst",
        ticker=ticker,
        end_date=end_date,
        evidence=evidence,
        claims=claims,
        signals=signals,
        narrative=fundamentals_report,
        meta={"extractor_version": version},
    )


__all__ = ["extract_fundamentals_evidence"]
