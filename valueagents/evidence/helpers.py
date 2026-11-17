# ./valueagents/evidence/helpers.py
"""Evidence 读取 helper — Phase 2 W2.0

提供 2 种视图：
  - get_evidence_view: 纯 evidence view（无 narrative fallback）
  - get_hybrid_view:   hybrid 模式（evidence claims + narrative 前段）

hybrid 模式目的：
  - evidence claims 提供精确结构化论点（便于 LLM 引用）
  - narrative 前段提供上下文（避免 LLM 只看 claim 列表而不理解语境）
  - 总长度可控（max_chars），降 token 又保信息

设计原则：
  - evidence 缺失时自动 fallback 到 narrative 截断（永远不返回空）
  - evidence view 生成失败时 fallback（不抛异常）
  - 输出长度严格 ≤ max_chars（防止 prompt 爆炸）
"""

from __future__ import annotations

from typing import Any, Optional

from .graph import EvidenceGraph


def get_evidence_view(
    artifacts: dict,
    key: str,
    view: str = "claims",
    max_chars: int = 3000,
) -> str:
    """纯 evidence view，fallback 到 narrative。

    Args:
        artifacts: 含 *_report 和 *_evidence 的 dict（LangGraph state 或 ctx.artifacts）
        key: "market" / "sentiment" / "news" / "fundamentals"
        view: "full" / "claims" / "signals" / "compact"
        max_chars: evidence view 输出上限

    Returns:
        evidence view 文本；evidence 空时返回 narrative 截断
    """
    evidence_dict = artifacts.get(f"{key}_evidence")
    if evidence_dict:
        try:
            return EvidenceGraph.from_dict(evidence_dict).to_view(
                view, max_chars=max_chars
            )
        except Exception as e:
            print(f"   [evidence] fallback to narrative for {key}: {e}")

    narrative = artifacts.get(f"{key}_report", "")
    if len(narrative) > max_chars:
        return narrative[: max_chars - 100] + "\n... [truncated]"
    return narrative


def get_hybrid_view(
    artifacts: dict,
    key: str,
    max_chars: int = 6000,
    evidence_ratio: float = 0.4,
) -> str:
    """Hybrid 视图：evidence claims + narrative 前段。

    Args:
        artifacts: LangGraph state dict
        key: "market" / "sentiment" / "news" / "fundamentals"
        max_chars: 输出总字符上限
        evidence_ratio: evidence 部分占总长度的比例（0.3-0.5）

    Returns:
        组合文本（## Structured Evidence + ## Full Report excerpt）；
        evidence 空时退化为 narrative 截断。
    """
    narrative = artifacts.get(f"{key}_report", "")
    evidence_dict = artifacts.get(f"{key}_evidence")

    # ---------- 无 evidence → 纯 narrative 截断 ----------
    if not evidence_dict:
        if len(narrative) > max_chars:
            return narrative[: max_chars - 100] + "\n... [truncated]"
        return narrative

    # ---------- 生成 evidence view ----------
    try:
        evidence_view = EvidenceGraph.from_dict(evidence_dict).to_view(
            "claims", max_chars=int(max_chars * evidence_ratio)
        )
    except Exception as e:
        print(f"   [evidence] hybrid fallback for {key}: {e}")
        if len(narrative) > max_chars:
            return narrative[: max_chars - 100] + "\n... [truncated]"
        return narrative

    # ---------- 计算 narrative 可用预算 ----------
    header = (
        f"## Structured Evidence ({key})\n"
        f"{evidence_view}\n\n"
        f"## Full Report (excerpt, {key})\n"
    )
    narrative_budget = max_chars - len(header) - 200  # 留余量防超限

    if narrative_budget <= 500:
        # evidence 太长 → 只返回 evidence（截断到 max_chars）
        return evidence_view[:max_chars]

    if len(narrative) > narrative_budget:
        narrative_snippet = narrative[:narrative_budget] + "\n... [truncated]"
    else:
        narrative_snippet = narrative

    return header + narrative_snippet


__all__ = ["get_evidence_view", "get_hybrid_view"]
