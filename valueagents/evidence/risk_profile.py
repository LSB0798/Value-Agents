# ./valueagents/evidence/risk_profile.py
"""Phase 3 W3a: RiskProfile（5 维度 + framework_views）

W3a 设计：
  - 纯规则聚合（0 LLM 调用）
  - 5 维度从 evidence_graph + framework_views 推导
  - scenarios / falsifiers / overall_weights 留空（W3b 由 LLM 填充）
  - rating 由 5 维度加权分数派生

维度映射（按 analyst 来源，不依赖 signal.dimension 标签）：
  - market_evidence       → trend
  - fundamentals_evidence → valuation
  - news_evidence         → catalyst
  - sentiment_evidence    → sentiment
  - framework_views       → tail_risk（找 tail_risk 组）
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from .frameworks import FrameworkView


# ============================================================
# 5 维度权重（加权和决定 overall verdict 和 rating）
# ============================================================
_DIMENSION_WEIGHTS: dict[str, float] = {
    "trend": 0.20,
    "valuation": 0.25,
    "tail_risk": 0.20,
    "catalyst": 0.15,
    "sentiment": 0.20,
}

# analyst key → 维度
_ANALYST_TO_DIMENSION: dict[str, str] = {
    "market": "trend",
    "fundamentals": "valuation",
    "news": "catalyst",
    "sentiment": "sentiment",
}

_DIRECTION_VALUE: dict[str, float] = {
    "bullish": 1.0,
    "neutral": 0.0,
    "bearish": -1.0,
}


# ============================================================
# 5 维度信号（比 EvidenceBundle.Signal 更宽松，不带 claim_ids 强制约束）
# ============================================================
class DimensionSignal(BaseModel):
    """RiskProfile 的单个维度摘要。"""

    dimension: str = Field(..., min_length=1)
    direction: Literal["bullish", "bearish", "neutral"] = "neutral"
    strength: float = Field(default=0.0, ge=0.0, le=1.0)
    contributing_signals: int = 0
    source_analysts: list[str] = Field(default_factory=list)
    key_claims: list[str] = Field(default_factory=list)
    note: str = ""


# ============================================================
# RiskProfile
# ============================================================
class RiskProfile(BaseModel):
    """5 维度风险画像 + 多框架视角。"""

    ticker: str = Field(..., min_length=1)
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")

    # ── 5 维度（W3a 纯规则产出） ──
    trend: DimensionSignal
    valuation: DimensionSignal
    tail_risk: DimensionSignal
    catalyst: DimensionSignal
    sentiment: DimensionSignal

    # ── framework_views（W1 产出） ──
    framework_views: dict[str, FrameworkView] = Field(default_factory=dict)

    # ── W3b LLM 填充（W3a 留空 / 默认值） ──
    scenarios: dict[str, float] = Field(
        default_factory=dict,
        description='{"bear": -0.1, "base": 0.02, "bull": 0.15}',
    )
    overall_weights: dict[str, float] = Field(
        default_factory=dict,
        description='{"buy": 0.3, "hold": 0.5, "sell": 0.2}',
    )
    falsifiers: list[str] = Field(
        default_factory=list,
        description="什么情况下决策会翻转（W3b 由 LLM 填）",
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # ── 派生主输出（兼容下游 Rating） ──
    overall_verdict: Literal["bullish", "bearish", "neutral"] = "neutral"
    overall_score: float = 0.0
    rating: str = "Hold"

    meta: dict[str, Any] = Field(default_factory=dict)

    def dimension_map(self) -> dict[str, DimensionSignal]:
        return {
            "trend": self.trend,
            "valuation": self.valuation,
            "tail_risk": self.tail_risk,
            "catalyst": self.catalyst,
            "sentiment": self.sentiment,
        }


# ============================================================
# 内部：从单个 analyst bundle 聚合一个维度
# ============================================================
def _aggregate_analyst_signals(
    bundle: Optional[dict[str, Any]],
    dimension: str,
    source_analyst: str,
) -> DimensionSignal:
    """从 bundle.signals 聚合出一个维度信号。"""
    if not bundle or not isinstance(bundle, dict):
        return DimensionSignal(
            dimension=dimension,
            direction="neutral",
            strength=0.0,
            contributing_signals=0,
            source_analysts=[source_analyst],
            note="no bundle",
        )

    signals = bundle.get("signals") or []
    if not signals:
        return DimensionSignal(
            dimension=dimension,
            direction="neutral",
            strength=0.0,
            contributing_signals=0,
            source_analysts=[source_analyst],
            note="no signals in bundle",
        )

    bullish: list[float] = []
    bearish: list[float] = []
    neutral: list[float] = []
    all_claim_ids: list[str] = []

    for sig in signals:
        if not isinstance(sig, dict):
            continue
        direction = str(sig.get("direction", "neutral")).lower()
        try:
            strength = float(sig.get("strength", 0.5) or 0)
        except (TypeError, ValueError):
            strength = 0.5
        strength = max(0.0, min(1.0, strength))
        if direction == "bullish":
            bullish.append(strength)
        elif direction == "bearish":
            bearish.append(strength)
        else:
            neutral.append(strength)
        claim_ids = sig.get("claim_ids") or []
        if isinstance(claim_ids, list):
            all_claim_ids.extend(claim_ids)

    n_bull, n_bear, n_neu = len(bullish), len(bearish), len(neutral)
    total = n_bull + n_bear + n_neu
    if total == 0:
        return DimensionSignal(
            dimension=dimension,
            direction="neutral",
            strength=0.0,
            contributing_signals=0,
            source_analysts=[source_analyst],
        )

    # 严格多数
    if n_bull > n_bear and n_bull > n_neu:
        verdict = "bullish"
        strength = sum(bullish) / n_bull
    elif n_bear > n_bull and n_bear > n_neu:
        verdict = "bearish"
        strength = sum(bearish) / n_bear
    else:
        verdict = "neutral"
        strength = 0.5

    return DimensionSignal(
        dimension=dimension,
        direction=verdict,  # type: ignore[arg-type]
        strength=max(0.0, min(1.0, strength)),
        contributing_signals=total,
        source_analysts=[source_analyst],
        key_claims=list(dict.fromkeys(all_claim_ids))[:5],  # 去重保序，最多 5 个
    )


# ============================================================
# 内部：tail_risk 从 framework_views 推导
# ============================================================
def _aggregate_tail_risk(framework_views: list[FrameworkView]) -> DimensionSignal:
    """从 framework_views 中找 tail_risk 组，或回退到 neutral。"""
    for v in framework_views:
        if v.framework_id == "tail_risk":
            return DimensionSignal(
                dimension="tail_risk",
                direction=v.verdict,
                strength=v.confidence,
                contributing_signals=len(v.contributing_masters),
                source_analysts=["tail_risk_framework"],
                note=f"from framework (masters={v.contributing_masters})",
            )
    return DimensionSignal(
        dimension="tail_risk",
        direction="neutral",
        strength=0.0,
        contributing_signals=0,
        source_analysts=["tail_risk_framework"],
        note="no tail_risk framework view available",
    )


# ============================================================
# 内部：5 维度 → overall_score / verdict / rating
# ============================================================
def _compute_overall_score(dims: dict[str, DimensionSignal]) -> float:
    """加权和，范围 [-1, 1]。"""
    score = 0.0
    for dim_name, weight in _DIMENSION_WEIGHTS.items():
        d = dims.get(dim_name)
        if d is None:
            continue
        score += weight * _DIRECTION_VALUE.get(d.direction, 0.0) * d.strength
    return max(-1.0, min(1.0, score))


def _score_to_verdict(score: float) -> str:
    if score > 0.2:
        return "bullish"
    if score < -0.2:
        return "bearish"
    return "neutral"


def _score_to_rating(score: float) -> str:
    if score > 0.4:
        return "Buy"
    if score > 0.15:
        return "Overweight"
    if score >= -0.15:
        return "Hold"
    if score >= -0.4:
        return "Underweight"
    return "Sell"


def _score_to_confidence(score: float, total_signals: int) -> float:
    """confidence = |score| * 信号覆盖修正。"""
    if total_signals == 0:
        return 0.0
    coverage = min(total_signals / 10.0, 1.0)  # 10+ 个信号视为满覆盖
    return max(0.0, min(1.0, abs(score) * coverage))


# ============================================================
# 主入口
# ============================================================
def build_risk_profile(
    ticker: str,
    end_date: str,
    evidence_graph: Optional[dict[str, Any]],
    framework_views: list[FrameworkView],
) -> RiskProfile:
    """从 evidence_graph + framework_views 构建 RiskProfile（纯规则，0 LLM）。

    Args:
        ticker / end_date: 上下文
        evidence_graph: {market: {...}, sentiment: {...}, news: {...}, fundamentals: {...}}
                        每个 {...} 是 EvidenceBundle.model_dump() 的输出。
                        缺失 key 或空 dict → 对应维度回退 neutral。
        framework_views: W1 产出的 list[FrameworkView]

    Returns:
        RiskProfile（scenarios / falsifiers / overall_weights 留空，W3b 填）
    """
    eg = evidence_graph or {}

    trend = _aggregate_analyst_signals(eg.get("market"), "trend", "market_analyst")
    valuation = _aggregate_analyst_signals(eg.get("fundamentals"), "valuation", "fundamentals_analyst")
    catalyst = _aggregate_analyst_signals(eg.get("news"), "catalyst", "news_analyst")
    sentiment = _aggregate_analyst_signals(eg.get("sentiment"), "sentiment", "sentiment_analyst")
    tail_risk = _aggregate_tail_risk(framework_views or [])

    dims = {
        "trend": trend,
        "valuation": valuation,
        "tail_risk": tail_risk,
        "catalyst": catalyst,
        "sentiment": sentiment,
    }

    overall_score = _compute_overall_score(dims)
    overall_verdict = _score_to_verdict(overall_score)
    rating = _score_to_rating(overall_score)

    total_signals = sum(d.contributing_signals for d in dims.values())
    confidence = _score_to_confidence(overall_score, total_signals)

    fw_dict = {v.framework_id: v for v in (framework_views or [])}

    return RiskProfile(
        ticker=ticker,
        end_date=end_date,
        trend=trend,
        valuation=valuation,
        tail_risk=tail_risk,
        catalyst=catalyst,
        sentiment=sentiment,
        framework_views=fw_dict,
        scenarios={},       # W3b 填
        overall_weights={},  # W3b 填
        falsifiers=[],       # W3b 填
        confidence=confidence,
        overall_verdict=overall_verdict,  # type: ignore[arg-type]
        overall_score=overall_score,
        rating=rating,
        meta={
            "builder": "w3a_rule_only",
            "total_signals": total_signals,
            "dimension_weights": _DIMENSION_WEIGHTS,
        },
    )


# ============================================================
# 摘要（供 prompt / log 用）
# ============================================================
def summarize_risk_profile(rp: RiskProfile) -> str:
    """RiskProfile → 简洁文本摘要。"""
    lines = [
        f"# Risk Profile — {rp.ticker} @ {rp.end_date}",
        f"# overall: {rp.overall_verdict} (score={rp.overall_score:+.2f}, "
        f"conf={rp.confidence:.2f}) → rating={rp.rating}",
        "",
        "## Dimensions",
    ]
    for name in ("trend", "valuation", "tail_risk", "catalyst", "sentiment"):
        d = rp.dimension_map()[name]
        lines.append(
            f"- {name:<12} {d.direction:<8} strength={d.strength:.2f} "
            f"signals={d.contributing_signals} src={d.source_analysts}"
        )

    if rp.framework_views:
        lines.append("")
        lines.append(f"## Framework Views ({len(rp.framework_views)} groups)")
        for fw_id, fw in rp.framework_views.items():
            lines.append(
                f"- [{fw_id}] {fw.verdict} conf={fw.confidence:.2f} "
                f"masters={len(fw.contributing_masters)}/{fw.total_masters_in_group}"
            )

    if rp.falsifiers:
        lines.append("")
        lines.append("## Falsifiers (what would flip this)")
        for f in rp.falsifiers:
            lines.append(f"- {f}")

    return "\n".join(lines)


__all__ = [
    "DimensionSignal",
    "RiskProfile",
    "build_risk_profile",
    "summarize_risk_profile",
]
