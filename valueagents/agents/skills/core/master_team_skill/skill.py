# valueagents/agents/skills/core/master_team_skill/skill.py
"""
Master Team Meta Skill (Phase 6a)。

串行调用用户选中的 N 个大师分析师，聚合 signals。
Phase 6b 会改成并发（需先解决 contextvars / 压缩器竞态）。
"""

import json
from valueagents.agents.skills.contract import SkillContext, SkillResult
from valueagents.agents.skills.runtime import set_current_llm, reset_current_llm


_REQUIRED_KEYS = (
    "company_of_interest",
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
)


def _validate_artifacts(ctx: SkillContext) -> list[str]:
    return [k for k in _REQUIRED_KEYS if k not in ctx.artifacts]


def execute(ctx: SkillContext) -> SkillResult:
    missing = _validate_artifacts(ctx)
    if missing:
        return SkillResult(
            outputs={"master_analyst_signals": {}, "master_summary": ""},
            metadata={"agent": "master_team", "error": f"missing: {missing}"},
        )

    # 🆕 Prefetch：串行预取所有共享数据源，让 19 个大师 skill 全走缓存
    from valueagents.agents.utils.prefetch import prefetch_shared_data
    prefetch_shared_data(ctx.ticker, ctx.end_date, ctx.api_key)

    # 从 config 读选中的大师列表
    cfg = ctx.config or {}
    master_analysts = cfg.get("master_analysts") or []

    # 兜底：若没指定，用默认 3 个
    if not master_analysts:
        master_analysts = [
            "warren_buffett_analyst",
            "charlie_munger_analyst",
            "ben_graham_analyst",
        ]

    from valueagents.agents.skills.registry import get_registry
    registry = get_registry()

    signals_flat: dict[str, dict] = {}
    signals_wrapped: dict[str, dict] = {}

    print(f"\n   🎩 [master_team] starting: {len(master_analysts)} masters")

    # 串行调用
    for master_name in master_analysts:
        tool = registry.get_tool(master_name)
        if tool is None:
            print(f"   ⚠️ [master_team] {master_name} not found, skipping")
            continue

        print(f"   🎩 [master_team] → {master_name}")
        token = set_current_llm(ctx.llm)
        try:
            # raw = tool.func(ticker=ctx.ticker, end_date=ctx.end_date, api_key=ctx.api_key,)

            call_kwargs = {"ticker": ctx.ticker, "end_date": ctx.end_date, "api_key": ctx.api_key}
            if master_name == "technical_analyst":
                # technical_analyst 需要 start_date
                from datetime import datetime, timedelta
                try:
                    dt = datetime.strptime(ctx.end_date, "%Y-%m-%d")
                    call_kwargs["start_date"] = (dt - timedelta(days=365)).strftime("%Y-%m-%d")
                except Exception:
                    call_kwargs["start_date"] = ctx.end_date
            raw = tool.func(**call_kwargs)

            parsed = _parse_master_output(raw)
            signals_flat[master_name] = parsed
            signals_wrapped[master_name] = {ctx.ticker: parsed}
            print(f"   🎩 [master_team] ✅ {master_name}: {parsed['signal']} "
                  f"(conf: {parsed['confidence']})")
        except Exception as e:
            print(f"   ⚠️ [master_team] {master_name} failed: {type(e).__name__}: {e}")
            fallback = {
                "signal": "neutral",
                "confidence": 0,
                "reasoning": f"failed: {e}",
            }
            signals_flat[master_name] = fallback
            signals_wrapped[master_name] = {ctx.ticker: fallback}
        finally:
            reset_current_llm(token)

    # 聚合
    summary = _aggregate(signals_flat)
    print(f"   🎩 [master_team] done: {summary}")

    return SkillResult(
        outputs={
            "master_analyst_signals": signals_wrapped,
            "master_summary": summary,
        },
        metadata={
            "agent": "master_team",
            "masters_count": len(signals_flat),
        },
    )


def _parse_master_output(raw) -> dict:
    """master skill 返回 JSON str，解析为 {signal, confidence, reasoning}。"""
    if isinstance(raw, dict):
        data = raw
    elif isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
    else:
        data = None

    if not isinstance(data, dict):
        return {
            "signal": "neutral",
            "confidence": 0,
            "reasoning": f"unparseable: {str(raw)[:200]}",
        }

    return {
        "signal": str(data.get("signal", "neutral")).lower(),
        "confidence": float(data.get("confidence", 0) or 0),
        "reasoning": str(data.get("reasoning", ""))[:500],
    }


def _aggregate(signals: dict[str, dict]) -> str:
    """聚合摘要。"""
    if not signals:
        return "(no master signals)"

    bullish = [n for n, s in signals.items() if s["signal"] == "bullish"]
    bearish = [n for n, s in signals.items() if s["signal"] == "bearish"]
    neutral = [n for n, s in signals.items() if s["signal"] == "neutral"]

    parts = [f"{len(signals)} masters analyzed"]
    if bullish:
        parts.append(f"bullish: {', '.join(bullish)}")
    if bearish:
        parts.append(f"bearish: {', '.join(bearish)}")
    if neutral:
        parts.append(f"neutral: {', '.join(neutral)}")

    return " | ".join(parts)
