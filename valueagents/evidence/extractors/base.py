# ./valueagents/evidence/extractors/base.py
"""提取器通用工具。"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any


def stable_hash(*parts: Any, length: int = 8) -> str:
    """稳定 hash，用于生成 evidence/claim ID 后缀。"""
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:length]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def make_evidence_id(source: str, content_preview: str) -> str:
    """生成符合 ev_xxx 格式的 ID。"""
    h = stable_hash(source, content_preview)
    return f"ev_{source.replace(':', '_').replace(' ', '_')[:20]}_{h}"


def make_claim_id(statement: str) -> str:
    h = stable_hash(statement)
    return f"cl_{h}"


def make_signal_id(ticker: str, dimension: str, framework: str | None, direction: str) -> str:
    h = stable_hash(ticker, dimension, framework or "", direction)
    return f"sig_{h}"


# ============================================================
# Phase 2 W1.6：通用 evidence 提取（供 4 个 extractor 复用）
# ============================================================
import sys
from typing import Any

from langchain_core.messages import ToolMessage
from valueagents.evidence.schema import EvidenceItem


_MAX_TOOL_TEXT_DEFAULT = 5000


def extract_evidence_items(
    messages: list[Any],
    max_text_len: int = _MAX_TOOL_TEXT_DEFAULT,
) -> list[EvidenceItem]:
    """从 messages 中提取所有 ToolMessage 作为 EvidenceItem。

    Args:
        messages: state["messages"] 列表
        max_text_len: 单个 tool 内容截断长度

    Returns:
        每个 ToolMessage 对应 1 个 EvidenceItem
    """
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
        preview = content_str[:max_text_len]

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
                    "truncated": len(content_str) > max_text_len,
                },
                raw_ref=f"tool_call:{tool_call_id}",
            )
        )

    return evidence