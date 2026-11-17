# ./valueagents/evidence/extractors/_llm.py
"""通用 LLM 提取器 — Phase 2 W1.5（v2：序号引用）

关键设计：
  - LLM 输出 claims（按顺序）+ signals（用 claim_refs 引用序号 C1/C2/...）
  - 后处理：把 claim_refs 映射到真实 hash id
  - 严格校验：evidence_ids 必须存在；claim_refs 必须能映射
  - 失败返回空，不抛异常
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from valueagents.evidence.schema import Claim, EvidenceItem, Signal
from .base import make_claim_id


_MAX_EVIDENCE_PREVIEW = 200
_MAX_NARRATIVE_CHARS = 8000


# ============================================================
# Prompt 构造
# ============================================================
def _format_evidence_list(evidence: list[EvidenceItem]) -> str:
    lines = []
    for ev in evidence:
        text = ev.content.get("text", "")[:_MAX_EVIDENCE_PREVIEW]
        text = text.replace("\n", " ")
        lines.append(f"- `{ev.id}` ({ev.source}): {text}")
    return "\n".join(lines) if lines else "(no evidence available)"


def _build_prompt(
    ticker: str,
    end_date: str,
    narrative: str,
    evidence: list[EvidenceItem],
    framework: str,
) -> str:
    narrative_snippet = narrative[:_MAX_NARRATIVE_CHARS]
    if len(narrative) > _MAX_NARRATIVE_CHARS:
        narrative_snippet += "\n\n... [narrative truncated]"

    evidence_block = _format_evidence_list(evidence)

    return f"""You are extracting structured claims and signals from a financial analysis report.

## Context
- Ticker: {ticker}
- Analysis date: {end_date}
- Framework: {framework}

## Available Evidence (you MUST only use these IDs)
{evidence_block}

## Narrative (the report to extract from)
<narrative>
{narrative_snippet}
</narrative>

## Task
Extract **3 to 8 claims** and **1 to 3 signals**.

### Claim rules
- Each claim must be ONE specific statement (not a summary paragraph).
- `evidence_ids`: MUST reference one or more IDs from the "Available Evidence" list above. At least 1.
- `confidence`: 0.0-1.0, how strongly the narrative supports this claim.

**IMPORTANT**: You will NOT assign claim IDs. Instead, the system assigns each claim an
index C1, C2, C3, ... in the ORDER you output them. The FIRST claim in your output
becomes C1, the SECOND becomes C2, and so on.

### Signal rules
- Each signal aggregates 1-3 claims into a direction.
- `direction`: one of "bullish", "bearish", "neutral".
- `strength`: 0.0-1.0.
- `claim_refs`: a list like `["C1", "C2"]`. Each ref MUST be one of the claim indices
  (C1, C2, ...) that you actually output above. At least 1 ref.
- `dimension`: a short label like "trend", "momentum", "volatility".
- `provenance`: one short sentence like "aggregated from 3 technical claims".

### Output format (STRICT JSON, no markdown fences, no explanation)
{{
  "claims": [
    {{
      "statement": "...",
      "confidence": 0.0-1.0,
      "evidence_ids": ["ev_xxx", "ev_yyy"],
      "framework": "{framework}"
    }}
  ],
  "signals": [
    {{
      "dimension": "trend",
      "direction": "bullish|bearish|neutral",
      "strength": 0.0-1.0,
      "claim_refs": ["C1", "C2"],
      "framework": "{framework}",
      "provenance": "..."
    }}
  ]
}}

Output ONLY the JSON object. No ```json fences. No explanation. Do NOT wrap in XML.
"""


# ============================================================
# JSON 解析
# ============================================================
def _try_parse_json(text: str) -> Optional[dict]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


# ============================================================
# 主入口
# ============================================================
def extract_claims_and_signals(
    llm: Any,
    ticker: str,
    end_date: str,
    narrative: str,
    evidence: list[EvidenceItem],
    framework: str = "technical",
) -> tuple[list[Claim], list[Signal]]:
    """调 LLM 提取 claim/signal，失败返回空。"""
    if not narrative or not evidence:
        return [], []

    prompt = _build_prompt(ticker, end_date, narrative, evidence, framework)

    try:
        response = llm.invoke(prompt)
        content = getattr(response, "content", str(response))
        data = _try_parse_json(content)
    except Exception as e:
        print(f"   ⚠️ [llm_extractor] LLM call failed: {type(e).__name__}: {e}")
        return [], []

    if not isinstance(data, dict):
        print(f"   ⚠️ [llm_extractor] unparseable output: {str(content)[:200]!r}")
        return [], []

    available_ev_ids = {ev.id for ev in evidence}
    raw_claims = data.get("claims") or []
    raw_signals = data.get("signals") or []

    # ---------- 过滤 claims，同时建立 C1/C2/... → 真实 hash id 映射 ----------
    valid_claims: list[Claim] = []
    claim_index_map: dict[str, str] = {}   # "C1" -> "cl_hash"
    for i, rc in enumerate(raw_claims, start=1):
        if not isinstance(rc, dict):
            continue
        stmt = str(rc.get("statement", "")).strip()
        if not stmt:
            continue
        ev_ids = rc.get("evidence_ids") or []
        if not isinstance(ev_ids, list) or not ev_ids:
            continue
        if not all(eid in available_ev_ids for eid in ev_ids):
            print(f"   ⚠️ [llm_extractor] dropping claim with hallucinated evidence_ids")
            continue
        try:
            conf = float(rc.get("confidence", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        conf = max(0.0, min(1.0, conf))

        cl_id = make_claim_id(stmt)
        try:
            cl = Claim(
                id=cl_id,
                statement=stmt,
                confidence=conf,
                evidence_ids=list(ev_ids),
                framework=rc.get("framework", framework),
            )
            valid_claims.append(cl)
            claim_index_map[f"C{i}"] = cl_id
        except Exception as e:
            print(f"   ⚠️ [llm_extractor] invalid claim: {e}")
            continue

    # ---------- 过滤 signals（用 claim_refs 映射到真实 id） ----------
    valid_signals: list[Signal] = []
    for rs in raw_signals:
        if not isinstance(rs, dict):
            continue
        direction = rs.get("direction", "").lower()
        if direction not in ("bullish", "bearish", "neutral"):
            continue

        claim_refs = rs.get("claim_refs") or []
        if not isinstance(claim_refs, list) or not claim_refs:
            print(f"   ⚠️ [llm_extractor] dropping signal with empty claim_refs")
            continue

        # 映射 C1/C2 -> 真实 hash id
        real_claim_ids: list[str] = []
        bad_refs: list[str] = []
        for ref in claim_refs:
            ref_key = str(ref).strip().upper()
            if ref_key in claim_index_map:
                real_claim_ids.append(claim_index_map[ref_key])
            else:
                bad_refs.append(ref_key)
        if bad_refs:
            print(f"   ⚠️ [llm_extractor] dropping signal with unknown claim_refs: {bad_refs}")
            continue
        if not real_claim_ids:
            continue

        try:
            strength = float(rs.get("strength", 0.5))
        except (TypeError, ValueError):
            strength = 0.5
        strength = max(0.0, min(1.0, strength))

        try:
            valid_signals.append(Signal(
                ticker=ticker,
                dimension=str(rs.get("dimension", "general")),
                framework=rs.get("framework", framework),
                direction=direction,
                strength=strength,
                claim_ids=real_claim_ids,
                provenance=str(rs.get("provenance", "")).strip() or "auto-extracted",
            ))
        except Exception as e:
            print(f"   ⚠️ [llm_extractor] invalid signal: {e}")
            continue

    return valid_claims, valid_signals


__all__ = ["extract_claims_and_signals"]
