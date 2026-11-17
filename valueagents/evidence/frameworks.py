# ./valueagents/evidence/frameworks.py
"""Phase 3 W1: FrameworkView + MASTER_GROUPS

把 19 个 master 归入 8 个框架组，每组产出 1 个 FrameworkView。

W1 设计：
  - 纯规则聚合（0 LLM 调用）
  - verdict = 多数投票；平局 → neutral
  - confidence = 投票给 verdict 的 master 的 confidence 平均
  - key_uncertainty / claims 留空（W3 才填）

W2 才把 framework_views 注入 Bull/Bear prompt。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================
# 命名兼容：master_signals 的 key 有两种写法
#   - skill 注册名：warren_buffett_analyst（_analyst 结尾）
#   - signal 输出名：warren_buffett_agent（_agent 结尾）
# hf_analysts_wrapper 会把前者转成后者，所以查 signal 时两种都要认。
# ============================================================
_SUFFIX_ANALYST = "_analyst"
_SUFFIX_AGENT = "_agent"


def _find_signal(master_name: str, master_signals: dict[str, Any]) -> Optional[Any]:
    """查 master_signals，兼容 _analyst / _agent 双向命名。"""
    if not master_signals:
        return None
    if master_name in master_signals:
        return master_signals[master_name]
    # _analyst → _agent
    if master_name.endswith(_SUFFIX_ANALYST):
        alt = master_name[: -len(_SUFFIX_ANALYST)] + _SUFFIX_AGENT
        if alt in master_signals:
            return master_signals[alt]
    # _agent → _analyst
    elif master_name.endswith(_SUFFIX_AGENT):
        alt = master_name[: -len(_SUFFIX_AGENT)] + _SUFFIX_ANALYST
        if alt in master_signals:
            return master_signals[alt]
    return None


# ============================================================
# 8 个框架组（19 master 全覆盖，无重复）
# ============================================================
MASTER_GROUPS: dict[str, list[str]] = {
    "intrinsic_value": [
        "warren_buffett_analyst",
        "charlie_munger_analyst",
        "ben_graham_analyst",
        "aswath_damodaran_analyst",
    ],
    "growth": [
        "cathie_wood_analyst",
        "peter_lynch_analyst",
        "phil_fisher_analyst",
        "growth_analyst",
    ],
    "deep_value": [
        "michael_burry_analyst",
        "mohnish_pabrai_analyst",
        "rakesh_jhunjhunwala_analyst",
    ],
    "quality": [
        "bill_ackman_analyst",
        "fundamental_analyst",
        "valuation_analyst",
    ],
    "tail_risk": ["nassim_taleb_analyst"],
    "macro_momentum": ["stanley_druckenmiller_analyst"],
    "technical": ["technical_analyst"],
    "sentiment": ["sentiment_analyst", "news_sentiment_analyst"],
}

# 19 master 的清单（用于单元测试校验）
ALL_19_MASTERS: set[str] = {
    "ben_graham_analyst", "warren_buffett_analyst", "charlie_munger_analyst",
    "peter_lynch_analyst", "phil_fisher_analyst", "bill_ackman_analyst",
    "michael_burry_analyst", "aswath_damodaran_analyst", "mohnish_pabrai_analyst",
    "nassim_taleb_analyst", "cathie_wood_analyst", "stanley_druckenmiller_analyst",
    "rakesh_jhunjhunwala_analyst", "fundamental_analyst", "growth_analyst",
    "news_sentiment_analyst", "sentiment_analyst", "technical_analyst",
    "valuation_analyst",
}


# ============================================================
# 每个 framework 的核心问题
# ============================================================
FRAMEWORK_QUESTIONS: dict[str, str] = {
    "intrinsic_value": "内在价值是否被显著低估，且存在足够的安全边际？",
    "growth": "公司能否在合理价格下持续高增长，以支撑当前估值？",
    "deep_value": "是否存在硬性数据支持的低估，且有明确的催化剂？",
    "quality": "业务质量、护城河和管理层质量是否足以支撑长期持有？",
    "tail_risk": "公司在极端事件下是否脆弱，或反脆弱（从混乱中受益）？",
    "macro_momentum": "宏观和价格动量是否支持当前趋势持续？",
    "technical": "技术面是否显示趋势、支撑阻力或动量出现关键转折？",
    "sentiment": "市场情绪和叙事是否与基本面脱节，或正在转向？",
}


# ============================================================
# 每个 framework 的失效场景
# ============================================================
FRAMEWORK_APPLICABLE_WHEN: dict[str, str] = {
    "intrinsic_value": "适用于成熟、盈利稳定、有可预测现金流的公司；不适用于早期或亏损公司。",
    "growth": "适用于高增长、可复利业务；不适用于成熟周期性行业。",
    "deep_value": "适用于有清晰资产负债表的低估公司；不适用于高杠杆或结构性衰退。",
    "quality": "适用于长期持有；不适用于短期事件交易。",
    "tail_risk": "适用于评估下行风险和非对称机会；不适用于稳健复利标的。",
    "macro_momentum": "适用于趋势明确的阶段；在震荡市中易失真。",
    "technical": "适用于短中期交易；不适用于长期价值判断。",
    "sentiment": "适用于捕捉叙事拐点；不适用于基本面锚定。",
}


# ============================================================
# FrameworkView Schema
# ============================================================
class FrameworkView(BaseModel):
    """单个 framework 的视角快照。

    W1 只做规则聚合；key_uncertainty 由 W3 的 LLM 填充。
    """

    framework_id: str = Field(..., min_length=1)
    core_question: str = ""
    verdict: Literal["bullish", "bearish", "neutral"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    contributing_masters: list[str] = Field(
        default_factory=list,
        description="投票给 verdict 的 master 名称",
    )
    total_masters_in_group: int = 0
    key_uncertainty: str = Field(
        default="",
        description="这个框架最不确定的点（W3 由 LLM 填）",
    )
    applicable_when: str = ""
    claims: list[dict[str, Any]] = Field(
        default_factory=list,
        description="来自 EvidenceGraph 的相关 claims（W3 才填）",
    )


# ============================================================
# 内部：兼容单层 / 双层 signal
# ============================================================
def _normalize_signal_entry(sig_data: Any) -> Optional[dict[str, Any]]:
    """兼容 {signal, confidence} 和 {ticker: {signal, confidence}}。"""
    if not isinstance(sig_data, dict):
        return None
    if "signal" in sig_data and "confidence" in sig_data:
        return {
            "signal": str(sig_data.get("signal", "neutral")).lower(),
            "confidence": float(sig_data.get("confidence", 0) or 0),
            "reasoning": str(sig_data.get("reasoning", "")),
        }
    # 双层：取第一个有 signal 的 ticker
    for v in sig_data.values():
        if isinstance(v, dict) and "signal" in v:
            return {
                "signal": str(v.get("signal", "neutral")).lower(),
                "confidence": float(v.get("confidence", 0) or 0),
                "reasoning": str(v.get("reasoning", "")),
            }
    return None


# ============================================================
# 内部：聚合一个 group
# ============================================================
def _aggregate_group_signals(
    master_names: list[str],
    master_signals: dict[str, Any],
) -> tuple[str, float, list[str], int]:
    """聚合一个 group 的 master signals。

    Returns:
        (verdict, confidence, contributing_masters, total_in_group)
    """
    bullish: list[tuple[str, float]] = []
    bearish: list[tuple[str, float]] = []
    neutral: list[tuple[str, float]] = []

    for name in master_names:
        raw = _find_signal(name, master_signals)
        norm = _normalize_signal_entry(raw)
        if norm is None:
            continue
        direction = norm["signal"]
        conf = norm["confidence"]
        if direction == "bullish":
            bullish.append((name, conf))
        elif direction == "bearish":
            bearish.append((name, conf))
        else:
            neutral.append((name, conf))

    n_bull, n_bear, n_neu = len(bullish), len(bearish), len(neutral)
    total = n_bull + n_bear + n_neu

    if total == 0:
        return "neutral", 0.0, [], 0

    # 严格多数（平局 → neutral）
    if n_bull > n_bear and n_bull > n_neu:
        verdict = "bullish"
        contributing = bullish
    elif n_bear > n_bull and n_bear > n_neu:
        verdict = "bearish"
        contributing = bearish
    else:
        verdict = "neutral"
        contributing = neutral or (bullish + bearish + neutral)

    if not contributing:
        return verdict, 0.5, [], total

    avg_conf = sum(c for _, c in contributing) / len(contributing) / 100.0
    names = [name for name, _ in contributing]
    return verdict, max(0.0, min(1.0, avg_conf)), names, total


# ============================================================
# 对外入口
# ============================================================
def build_framework_views(
    master_signals: dict[str, Any],
    enabled_groups: Optional[list[str]] = None,
) -> list[FrameworkView]:
    """从 19 master 的 signals 构建 FrameworkView 列表。

    Args:
        master_signals: {master_name: signal_data}，signal_data 单层或双层均可
        enabled_groups: 只构建这些 group（None = 全部有数据的 group）

    Returns:
        FrameworkView 列表（只含有数据的 group）
    """
    if not master_signals:
        return []

    targets = enabled_groups if enabled_groups is not None else list(MASTER_GROUPS.keys())
    views: list[FrameworkView] = []

    for group_id in targets:
        if group_id not in MASTER_GROUPS:
            continue
        master_names = MASTER_GROUPS[group_id]
        verdict, confidence, contributing, total = _aggregate_group_signals(
            master_names, master_signals
        )
        if total == 0:
            continue

        views.append(
            FrameworkView(
                framework_id=group_id,
                core_question=FRAMEWORK_QUESTIONS.get(group_id, ""),
                verdict=verdict,  # type: ignore[arg-type]
                confidence=confidence,
                contributing_masters=contributing,
                total_masters_in_group=total,
                key_uncertainty="",   # W3 由 LLM 填
                applicable_when=FRAMEWORK_APPLICABLE_WHEN.get(group_id, ""),
                claims=[],            # W3 从 evidence_graph 关联
            )
        )

    return views


def summarize_framework_views(views: list[FrameworkView]) -> str:
    """FrameworkView 列表 → 简洁文本摘要（供 prompt / log 用）。"""
    if not views:
        return "(no framework views)"
    lines: list[str] = []
    for v in views:
        lines.append(
            f"- [{v.framework_id}] {v.verdict} "
            f"(conf={v.confidence:.2f}, "
            f"masters={len(v.contributing_masters)}/{v.total_masters_in_group})"
        )
        if v.core_question:
            lines.append(f"  Q: {v.core_question}")
    return "\n".join(lines)


__all__ = [
    "MASTER_GROUPS",
    "ALL_19_MASTERS",
    "FRAMEWORK_QUESTIONS",
    "FRAMEWORK_APPLICABLE_WHEN",
    "FrameworkView",
    "build_framework_views",
    "summarize_framework_views",
]
