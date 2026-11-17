# ./tests/unit/test_reflection.py
"""Phase 4 W3 Reflection 单元测试。"""

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from valueagents.learning.schema import DecisionRecord, OutcomeDetails
from valueagents.learning.reflection import (
    Reflection,
    ReflectionNote,
    get_reflections_dir,
)


def _make_record(
    decision_id="dec_test",
    rating="Buy",
    outcome="wrong",
    return_pct=-0.10,
) -> DecisionRecord:
    return DecisionRecord(
        decision_id=decision_id,
        ticker="NFLX",
        end_date="2026-09-03",
        timestamp=datetime.now(timezone.utc),
        final_rating=rating,
        outcome=outcome,
        outcome_details=OutcomeDetails(
            horizon="3m",
            price_at_decision=80.0,
            price_at_check=72.0,
            return_pct=return_pct,
            rating=rating,
            threshold_used=0.03,
        ) if outcome != "pending" else None,
    )


@pytest.fixture
def tmp_reflections(tmp_path, monkeypatch):
    """把 reflections 目录指向 tmp_path。"""
    monkeypatch.setenv("VALUEAGENTS_REFLECTIONS_DIR", str(tmp_path))
    yield tmp_path


# ============================================================
# 1. 规则生成
# ============================================================
def test_rule_based_reflection_buy(tmp_reflections):
    """Buy + 负收益 → 规则生成 what/lesson。"""
    r = Reflection(llm=None)
    rec = _make_record(rating="Buy", outcome="wrong", return_pct=-0.10)
    note = r.review_decision(rec)
    assert note is not None
    assert note.decision_id == "dec_test"
    assert note.rating == "Buy"
    assert note.actual_return_pct == pytest.approx(-10.0)
    assert "偏乐观" in note.what_went_wrong
    assert note.lesson
    assert note.generated_by == "rule"


def test_rule_based_reflection_sell(tmp_reflections):
    """Sell + 正收益 → 规则生成偏悲观。"""
    r = Reflection(llm=None)
    rec = _make_record(rating="Sell", outcome="wrong", return_pct=0.15)
    note = r.review_decision(rec)
    assert note is not None
    assert "偏悲观" in note.what_went_wrong


# ============================================================
# 2. 非 wrong 决策跳过
# ============================================================
def test_pending_skipped():
    r = Reflection(llm=None)
    rec = _make_record(outcome="pending")
    assert r.review_decision(rec) is None


def test_right_skipped():
    r = Reflection(llm=None)
    rec = _make_record(outcome="right")
    assert r.review_decision(rec) is None


# ============================================================
# 3. 幂等：同 decision_id 只处理一次
# ============================================================
def test_idempotent(tmp_reflections):
    r = Reflection(llm=None)
    rec = _make_record()
    note1 = r.review_decision(rec)
    note2 = r.review_decision(rec)   # 第二次应该返回 None
    assert note1 is not None
    assert note2 is None


# ============================================================
# 4. 存档 + 加载
# ============================================================
def test_save_and_load(tmp_reflections):
    r = Reflection(llm=None)
    rec = _make_record(decision_id="dec_a")
    note = r.review_decision(rec)

    assert note is not None
    # 文件存在
    files = list(tmp_reflections.glob("*.json"))
    assert len(files) == 1

    # 加载
    r2 = Reflection(llm=None)
    loaded = r2.load_all()
    assert len(loaded) == 1
    assert loaded[0].decision_id == "dec_a"


def test_load_for_ticker(tmp_reflections):
    r = Reflection(llm=None)
    r.review_decision(_make_record(decision_id="dec_nflx"))
    # 手工造一个不同 ticker 的
    other = _make_record(decision_id="dec_googl")
    other.ticker = "GOOGL"
    r.review_decision(other)

    assert len(r.load_all()) == 2
    assert len(r.load_for_ticker("NFLX")) == 1
    assert len(r.load_for_ticker("GOOGL")) == 1
    assert len(r.load_for_ticker("MSFT")) == 0


# ============================================================
# 5. get_lessons_text
# ============================================================
def test_lessons_text_empty(tmp_reflections):
    r = Reflection(llm=None)
    assert r.get_lessons_text() == ""


def test_lessons_text_has_content(tmp_reflections):
    r = Reflection(llm=None)
    r.review_decision(_make_record(decision_id="dec_a"))
    text = r.get_lessons_text()
    assert text
    assert "NFLX" in text
    # 规则生成的 lesson 是中文"当分析...的情境时..."
    assert "当分析" in text or "需要重新审视" in text


# ============================================================
# 6. LLM 失败回退规则
# ============================================================
def test_llm_failure_fallback_to_rule(tmp_reflections):
    """LLM 抛异常 → 回退规则生成。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("LLM down")

    r = Reflection(llm=llm)
    rec = _make_record(decision_id="dec_llm_fail")
    note = r.review_decision(rec)
    assert note is not None
    assert note.generated_by == "rule"


def test_llm_unparseable_fallback_to_rule(tmp_reflections):
    """LLM 返回非 JSON → 回退规则生成。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    resp = MagicMock()
    resp.content = "not json at all"
    llm.invoke.return_value = resp

    r = Reflection(llm=llm)
    rec = _make_record(decision_id="dec_llm_bad")
    note = r.review_decision(rec)
    assert note is not None
    assert note.generated_by == "rule"


def test_llm_success(tmp_reflections):
    """LLM 返回合法 JSON → generated_by="llm"。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    resp = MagicMock()
    resp.content = '{"what_went_wrong": "Over-optimistic on ad revenue ramp", "lesson": "Wait for 2 quarters of ad revenue data before upgrading"}'
    llm.invoke.return_value = resp

    r = Reflection(llm=llm)
    rec = _make_record(decision_id="dec_llm_ok")
    note = r.review_decision(rec)
    assert note is not None
    assert note.generated_by == "llm"
    assert "ad revenue" in note.what_went_wrong.lower()


# ============================================================
# 7. inject_to_memory（mock）
# ============================================================
def test_inject_to_memory(tmp_reflections):
    from unittest.mock import MagicMock

    r = Reflection(llm=None)
    r.review_decision(_make_record(decision_id="dec_a"))
    r.review_decision(_make_record(decision_id="dec_b"))

    mem = MagicMock()
    n = r.inject_to_memory(mem)
    assert n == 2
    assert mem.add_situations.called
    situations = mem.add_situations.call_args[0][0]
    assert len(situations) == 2
    # 每条是 (situation, recommendation) 的元组
    for s, rec in situations:
        assert "NFLX" in s
        assert "[PAST MISTAKE]" in rec


def test_inject_to_memory_empty(tmp_reflections):
    from unittest.mock import MagicMock
    r = Reflection(llm=None)
    mem = MagicMock()
    n = r.inject_to_memory(mem)
    assert n == 0
    assert not mem.add_situations.called


# ============================================================
# 8. review_all_wrong（mock load_decisions）
# ============================================================
def test_review_all_wrong(tmp_reflections, monkeypatch):
    """批量处理 wrong 决策。"""
    wrong_records = [
        _make_record(decision_id="dec_1", outcome="wrong"),
        _make_record(decision_id="dec_2", outcome="wrong"),
        _make_record(decision_id="dec_3", outcome="right"),
    ]
    monkeypatch.setattr(
        "valueagents.learning.reflection.load_decisions",
        lambda **kw: wrong_records,
    )

    r = Reflection(llm=None)
    notes = r.review_all_wrong()
    assert len(notes) == 2   # 只处理 2 个 wrong


def test_review_all_wrong_empty(tmp_reflections, monkeypatch):
    monkeypatch.setattr(
        "valueagents.learning.reflection.load_decisions",
        lambda **kw: [],
    )
    r = Reflection(llm=None)
    assert r.review_all_wrong() == []
