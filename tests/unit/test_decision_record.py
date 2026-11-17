"""Phase 2.5 DecisionRecord 单元测试。"""
# ./tests/unit/test_decision_record.py

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from valueagents.learning.schema import DecisionRecord, OutcomeDetails
from valueagents.learning.recorder import (
    record_decision, load_decisions, get_decisions_dir,
)


def test_decision_record_schema():
    """DecisionRecord 最小字段能构造。"""
    rec = DecisionRecord(
        decision_id="dec_test",
        ticker="NFLX",
        end_date="2026-09-03",
        timestamp=datetime.now(timezone.utc),
        final_rating="Buy",
    )
    assert rec.reasoning_mode == "legacy"
    assert rec.outcome == "pending"
    assert rec.evidence_graph == {}


def test_decision_record_invalid_date():
    """end_date 格式错 → 报错。"""
    with pytest.raises(Exception):
        DecisionRecord(
            decision_id="dec_test",
            ticker="NFLX",
            end_date="2026/09/03",
            timestamp=datetime.now(timezone.utc),
            final_rating="Buy",
        )


def test_record_and_load(tmp_path, monkeypatch):
    """record_decision 写入 + load_decisions 读回。"""
    monkeypatch.setenv("VALUEAGENTS_DECISIONS_DIR", str(tmp_path))

    rec = record_decision(
        ticker="NFLX",
        end_date="2026-09-03",
        final_rating="Buy",
        evidence_graph={"market": {"claims": []}},
        master_signals={"buffett": {"signal": "bullish"}},
        meta={"case_id": "B1"},
    )
    assert rec is not None
    assert rec.decision_id.startswith("dec_")

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1

    loaded = load_decisions()
    assert len(loaded) == 1
    assert loaded[0].ticker == "NFLX"
    assert loaded[0].final_rating == "Buy"


def test_load_decisions_filter(tmp_path, monkeypatch):
    """load_decisions 的 ticker / since / mode 过滤。"""
    monkeypatch.setenv("VALUEAGENTS_DECISIONS_DIR", str(tmp_path))

    record_decision("NFLX", "2026-09-03", "Buy", meta={"case_id": "B1"})
    record_decision("GOOGL", "2026-09-10", "Sell", meta={"case_id": "B2"})

    assert len(load_decisions()) == 2
    assert len(load_decisions(ticker="NFLX")) == 1
    assert len(load_decisions(since="2026-09-05")) == 1
    assert len(load_decisions(mode="legacy")) == 2
    assert len(load_decisions(mode="framework")) == 0
