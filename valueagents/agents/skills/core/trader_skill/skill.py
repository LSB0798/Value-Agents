# valueagents/agents/skills/core/trader_skill/skill.py
"""
Trader Core Skill

把 valueagents.agents.trader.trader.create_trader
包装为 SkillContext -> SkillResult。

与 research_manager / portfolio_manager 的差异：
  - create_trader 返回 functools.partial，agent_node(state) 直接可调（name 已绑定）
  - 返回 3 个字段：messages + trader_investment_plan + sender
  - 输入只需 4 份 report + investment_plan（不需要 debate_state / risk_debate_state）
  - 无 tool loop：单次 llm.invoke

与 4 个 analyst skill 的差异：
  - 无 tool loop（analyst 有 run_agent_with_tools）
  - 需要 memory（analyst 不需要）
  - LLM 用 quick_think（同 analyst，但 setup.py 需显式传对）
"""

import re

from valueagents.agents.skills.contract import SkillContext, SkillResult


# ============================================================
# 空 memory 兜底
# ============================================================

class _NullMemory:
    """与 FinancialSituationMemory 接口兼容的空实现。"""

    def get_memories(self, situation, n_matches=2):
        return []

    def add_situations(self, situations):
        pass


def _extract_text(content) -> str:
    """兼容 str / list[dict{type:'text'}] / list[str] / 其他。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    return str(content)


# ============================================================
# 前置依赖校验
# ============================================================

_REQUIRED_KEYS = (
    "company_of_interest",
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
    "investment_plan",
)

_FINAL_PROPOSAL_RE = re.compile(
    r"FINAL TRANSACTION PROPOSAL:\s*\**\s*(BUY|HOLD|SELL)", re.IGNORECASE
)


def _validate_artifacts(ctx: SkillContext) -> list[str]:
    return [k for k in _REQUIRED_KEYS if k not in ctx.artifacts]


# ============================================================
# 主入口
# ============================================================

def execute(ctx: SkillContext) -> SkillResult:
    missing = _validate_artifacts(ctx)
    if missing:
        return SkillResult(
            outputs={
                "trader_investment_plan": "",
                "messages": [],
                "sender": "Trader",
            },
            metadata={
                "agent": "trader",
                "error": f"missing required artifacts: {missing}",
            },
        )

    # 延迟 import：避免 skills.core 加载时触发循环
    from valueagents.agents.trader.trader import create_trader

    # 1) memory：优先从 artifacts 拿真 memory，否则用空实现
    memory = ctx.artifacts.get("_trader_memory")
    if memory is None:
        print("   [trader_skill] _trader_memory not provided; using _NullMemory")
        memory = _NullMemory()

    # 2) 构造 agent_node
    #    ⚠️ create_trader 返回 functools.partial(trader_node, name="Trader")
    #    直接 agent_node(state) 即可，不要传 name（否则 TypeError: multiple values）
    agent_node = create_trader(ctx.llm, memory)

    # 3) 单次调用（无 tool loop）
    result_state = agent_node(dict(ctx.artifacts))

    # 4) 提取 3 个输出
    trader_plan = _extract_text(result_state.get("trader_investment_plan", ""))
    new_messages = result_state.get("messages", [])
    sender = result_state.get("sender", "Trader")

    # 5) 兜底：交易计划为空
    if not trader_plan:
        print("   ⚠️ [trader_skill] empty trader_investment_plan returned")
        trader_plan = (
            "Trader plan unavailable: trader produced empty output. "
            "FINAL TRANSACTION PROPOSAL: **HOLD**"
        )

    # 6) 校验 FINAL TRANSACTION PROPOSAL（下游 SignalProcessor 依赖）
    has_final_proposal = bool(_FINAL_PROPOSAL_RE.search(trader_plan))
    if not has_final_proposal:
        print("   ⚠️ [trader_skill] missing 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**'")
        # 不强行追加（保持原始输出），只记录 metadata 供诊断

    return SkillResult(
        outputs={
            "trader_investment_plan": trader_plan,
            # 对齐老行为：返回 [result]；LangGraph operator.add 会累积
            "messages": new_messages,
            "sender": sender,
        },
        metadata={
            "agent": "trader",
            "plan_length": len(trader_plan),
            "has_final_proposal": has_final_proposal,
            "total_messages": len(new_messages),
        },
    )
