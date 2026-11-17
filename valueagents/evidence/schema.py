# ./valueagents/evidence/schema.py
"""Evidence Schema — Phase 1 F1.1

三层强制约束：EvidenceItem → Claim → Signal。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class EvidenceItem(BaseModel):
    """原子证据 —— 必须是事实，不可凭空产生。"""
    id: str = Field(..., pattern=r"^ev_[a-z0-9_]+$")
    source: str
    source_type: Literal["agent", "external", "computed"]
    timestamp: datetime
    content: dict[str, Any]
    raw_ref: str = Field(..., min_length=1)


class Claim(BaseModel):
    """主张 —— 必须有证据支撑。"""
    id: str = Field(..., pattern=r"^cl_[a-z0-9_]+$")
    statement: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(..., min_length=1)
    framework: str
    counter_claim_ids: list[str] = Field(default_factory=list)


class Signal(BaseModel):
    """从 claim 聚合的信号。"""
    ticker: str = Field(..., min_length=1)
    dimension: str
    framework: Optional[str] = None
    direction: Literal["bullish", "bearish", "neutral"]
    strength: float = Field(..., ge=0.0, le=1.0)
    claim_ids: list[str] = Field(..., min_length=1)
    provenance: str = Field(..., min_length=1)


class EvidenceBundle(BaseModel):
    """单个 agent 的完整证据包。"""
    agent_id: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1)
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    evidence: list[EvidenceItem] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    narrative: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_chain(self) -> "EvidenceBundle":
        ev_ids = {ev.id for ev in self.evidence}
        cl_ids = {cl.id for cl in self.claims}
        for cl in self.claims:
            missing = set(cl.evidence_ids) - ev_ids
            if missing:
                raise ValueError(
                    f"Claim {cl.id!r} references missing evidence: {sorted(missing)}"
                )
        for sig in self.signals:
            missing = set(sig.claim_ids) - cl_ids
            if missing:
                raise ValueError(
                    f"Signal {sig.dimension!r} references missing claims: {sorted(missing)}"
                )
        for cl in self.claims:
            missing = set(cl.counter_claim_ids) - cl_ids
            if missing:
                raise ValueError(
                    f"Claim {cl.id!r} references missing counter claims: {sorted(missing)}"
                )
        return self
