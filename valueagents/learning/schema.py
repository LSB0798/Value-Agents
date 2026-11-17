# ./valueagents/learning/schema.py
"""DecisionRecord Schema — Phase 2.5

归档每次决策的完整快照，用于：
  - Phase 3 Backtest 回测验收
  - Phase 4 Learning Weights
  - 人工审计历史决策链
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


OutcomeStatus = Literal["right", "wrong", "neutral", "pending"]


class OutcomeDetails(BaseModel):
    """单次决策的 outcome 详情。"""
    horizon: Literal["1m", "3m", "6m"]
    price_at_decision: float
    price_at_check: float
    return_pct: float
    rating: str  # Buy / Overweight / Hold / Underweight / Sell
    threshold_used: float


class DecisionRecord(BaseModel):
    """单次决策的完整快照。"""

    # ── 标识 ──
    decision_id: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1)
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    timestamp: datetime

    # ── 决策输入快照 ──
    evidence_graph: dict[str, Any] = Field(
        default_factory=dict,
        description="EvidenceGraph.to_dict() 的完整快照",
    )
    master_signals: dict[str, Any] = Field(
        default_factory=dict,
        description="19 个 master 的原始 signals",
    )
    risk_profile: Optional[dict[str, Any]] = Field(
        default=None,
        description="Phase 3 才填充",
    )

    # ── 决策输出 ──
    final_rating: str = Field(..., min_length=1)
    reasoning_mode: Literal["legacy", "framework", "ab"] = "legacy"

    # ── 反馈字段（后续由 OutcomeTracker 填充） ──
    price_at_decision: Optional[float] = None
    price_at_1m: Optional[float] = None
    price_at_3m: Optional[float] = None
    price_at_6m: Optional[float] = None

    outcome: OutcomeStatus = "pending"
    outcome_details: Optional[OutcomeDetails] = None

    # ── 元信息 ──
    meta: dict[str, Any] = Field(default_factory=dict)
