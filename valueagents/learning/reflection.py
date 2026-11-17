# ./valueagents/learning/reflection.py
"""Phase 4 W3: Reflection（错误反思 → Lesson 生成）

职责：
  1. 对 outcome="wrong" 的 DecisionRecord 生成 ReflectionNote
  2. ReflectionNote 存档到 valueagents/learning/reflections/{decision_id}.json
  3. 提供 CLI 可用 API：加载、生成、注入 memory

设计约束：
  - 不改 pipeline（RM/PM 已经在用 memory，只是往 memory 里塞数据）
  - LLM 可选（None 时用规则生成 lesson）
  - 失败不影响调用方
  - 幂等：已处理过的 decision_id 跳过
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from .recorder import load_decisions
from .schema import DecisionRecord


_REFLECTIONS_DIR_DEFAULT = Path(__file__).parent / "reflections"


# ============================================================
# Schema
# ============================================================
class ReflectionNote(BaseModel):
    """单条错误反思。"""

    decision_id: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1)
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    rating: str = Field(..., min_length=1)
    actual_return_pct: float = 0.0
    what_went_wrong: str = ""
    lesson: str = ""
    generated_by: str = "rule"   # "rule" / "llm"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def get_reflections_dir() -> Path:
    """获取反思存档目录（可被环境变量覆盖）。"""
    import os
    override = os.environ.get("VALUEAGENTS_REFLECTIONS_DIR", "").strip()
    d = Path(override) if override else _REFLECTIONS_DIR_DEFAULT
    d.mkdir(parents=True, exist_ok=True)
    return d


# ============================================================
# 规则生成（llm=None）
# ============================================================
def _rule_based_reflection(record: DecisionRecord) -> ReflectionNote:
    """无 LLM 时的规则生成。"""
    details = record.outcome_details
    ret_pct = 0.0
    if details and details.return_pct is not None:
        ret_pct = float(details.return_pct) * 100.0

    if record.final_rating in ("Buy", "Overweight"):
        wrong_side = "评级偏乐观"
    elif record.final_rating in ("Sell", "Underweight"):
        wrong_side = "评级偏悲观"
    else:
        wrong_side = "评级偏中性"

    what = (
        f"决策评级为 {record.final_rating}，实际 3 个月收益 {ret_pct:+.1f}%，"
        f"{wrong_side}。"
    )
    lesson = (
        f"当分析 {record.ticker} 在 {record.end_date} 的情境时，"
        f"若给出 {record.final_rating} 评级，需要重新审视风险与催化剂的权重平衡，"
        f"本次实际收益 {ret_pct:+.1f}% 提示方向判断有误。"
    )

    return ReflectionNote(
        decision_id=record.decision_id,
        ticker=record.ticker,
        end_date=record.end_date,
        rating=record.final_rating,
        actual_return_pct=ret_pct,
        what_went_wrong=what,
        lesson=lesson,
        generated_by="rule",
    )


# ============================================================
# LLM 生成
# ============================================================
_REFLECTION_PROMPT = """You are reviewing a past investment decision that went WRONG.

<decision>
Ticker: {ticker}
Date: {end_date}
Rating given: {rating}
Actual 3-month return: {ret_pct:+.1f}%
</decision>

Task: In 1-2 sentences, explain WHY the decision was wrong and what lesson should be applied to future similar decisions. Be specific about the cognitive or analytical error. Do NOT rehash the decision content.

Output JSON only (no markdown fences, no explanation):
{{
  "what_went_wrong": "one sentence on the specific error",
  "lesson": "one actionable lesson for future similar situations"
}}
"""


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


def _llm_based_reflection(
    record: DecisionRecord, llm: Any
) -> Optional[ReflectionNote]:
    """用 LLM 生成反思。失败返回 None。"""
    details = record.outcome_details
    ret_pct = 0.0
    if details and details.return_pct is not None:
        ret_pct = float(details.return_pct) * 100.0

    prompt = _REFLECTION_PROMPT.format(
        ticker=record.ticker,
        end_date=record.end_date,
        rating=record.final_rating,
        ret_pct=ret_pct,
    )

    try:
        resp = llm.invoke(prompt)
        content = getattr(resp, "content", str(resp))
        data = _try_parse_json(content)
    except Exception as e:
        print(f"   ⚠️ [Reflection] LLM call failed: {type(e).__name__}: {e}")
        return None

    if not isinstance(data, dict):
        return None

    what = str(data.get("what_went_wrong", "")).strip()
    lesson = str(data.get("lesson", "")).strip()
    if not what or not lesson:
        return None

    return ReflectionNote(
        decision_id=record.decision_id,
        ticker=record.ticker,
        end_date=record.end_date,
        rating=record.final_rating,
        actual_return_pct=ret_pct,
        what_went_wrong=what[:500],
        lesson=lesson[:500],
        generated_by="llm",
    )


# ============================================================
# Reflection 主类
# ============================================================
class Reflection:
    """错误反思管理器。"""

    def __init__(self, llm: Optional[Any] = None):
        self._llm = llm
        self._dir = get_reflections_dir()

    # ---------- 生成 ----------
    def review_decision(self, record: DecisionRecord) -> Optional[ReflectionNote]:
        """对单条 wrong 决策生成反思。"""
        if record.outcome != "wrong":
            return None
        if self._exists(record.decision_id):
            return None  # 幂等

        note: Optional[ReflectionNote] = None
        if self._llm is not None:
            note = _llm_based_reflection(record, self._llm)
        if note is None:
            note = _rule_based_reflection(record)

        self._save(note)
        return note

    def review_all_wrong(
        self, limit: int = 100
    ) -> list[ReflectionNote]:
        """扫描所有 wrong 决策，生成反思。"""
        decisions = load_decisions()
        wrong = [d for d in decisions if d.outcome == "wrong"]
        if not wrong:
            print("   [Reflection] no wrong decisions — skip")
            return []

        notes: list[ReflectionNote] = []
        for d in wrong[:limit]:
            note = self.review_decision(d)
            if note:
                notes.append(note)

        print(
            f"   [Reflection] processed {len(wrong[:limit])} wrong decisions, "
            f"new notes={len(notes)}"
        )
        return notes

    # ---------- 存档 ----------
    def _path(self, decision_id: str) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", decision_id)
        return self._dir / f"{safe}.json"

    def _exists(self, decision_id: str) -> bool:
        return self._path(decision_id).exists()

    def _save(self, note: ReflectionNote) -> None:
        try:
            self._path(note.decision_id).write_text(
                json.dumps(note.model_dump(mode="json"), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"   ⚠️ [Reflection] save failed: {e}")

    # ---------- 加载 ----------
    def load_all(self) -> list[ReflectionNote]:
        """从存档加载所有反思。"""
        notes: list[ReflectionNote] = []
        for f in self._dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                notes.append(ReflectionNote(**data))
            except Exception:
                continue
        notes.sort(key=lambda n: n.created_at, reverse=True)
        return notes

    def load_for_ticker(self, ticker: str) -> list[ReflectionNote]:
        return [n for n in self.load_all() if n.ticker == ticker]

    # ---------- 注入 memory ----------
    def inject_to_memory(self, memory: Any, ticker: Optional[str] = None) -> int:
        """把反思注入到 FinancialSituationMemory。

        Args:
            memory: FinancialSituationMemory 实例（需支持 add_situations）
            ticker: 只注入该 ticker 的反思（None = 全部）

        Returns:
            注入条数
        """
        if memory is None:
            return 0
        notes = self.load_for_ticker(ticker) if ticker else self.load_all()
        if not notes:
            return 0

        situations: list[tuple[str, str]] = []
        for n in notes:
            # situation：组合 ticker + rating + end_date 作为情境描述
            situation = (
                f"Analysis for {n.ticker} on {n.end_date}, "
                f"previous rating was {n.rating}."
            )
            # recommendation：把 lesson 作为"过去决策的教训"
            recommendation = (
                f"[PAST MISTAKE] {n.what_went_wrong} → Lesson: {n.lesson}"
            )
            situations.append((situation, recommendation))

        try:
            memory.add_situations(situations)
            print(f"   [Reflection] injected {len(situations)} notes into memory")
            return len(situations)
        except Exception as e:
            print(f"   ⚠️ [Reflection] inject to memory failed: {e}")
            return 0

    # ---------- 便于下游读 ----------
    def get_lessons_text(
        self, ticker: Optional[str] = None, max_notes: int = 5
    ) -> str:
        """返回 lessons 文本（可直接作为 past_lessons 注入 prompt）。"""
        notes = self.load_for_ticker(ticker) if ticker else self.load_all()
        if not notes:
            return ""
        lines: list[str] = []
        for n in notes[:max_notes]:
            lines.append(
                f"- [{n.ticker} @ {n.end_date}] {n.what_went_wrong} "
                f"→ {n.lesson}"
            )
        return "\n".join(lines)


__all__ = [
    "ReflectionNote",
    "Reflection",
    "get_reflections_dir",
]
