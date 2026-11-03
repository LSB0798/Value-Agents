# valueagents/agents/skills/core/portfolio_manager_skill/skill.py
"""
Portfolio Manager Core Skill

把 valueagents.agents.managers.portfolio_manager.create_portfolio_manager
包装为 SkillContext -> SkillResult。

与 research_manager_skill 的差异：
  - agent 函数名：create_portfolio_manager
  - memory key：_portfolio_manager_memory
  - 输入：investment_plan + trader_investment_plan + risk_debate_state（多了 trader_plan）
  - 输出：final_trade_decision + risk_debate_state
  - 无 tool loop：单次 llm.invoke
"""

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
    "trader_investment_plan",
    "risk_debate_state",
)


def _validate_artifacts(ctx: SkillContext) -> list[str]:
    """返回缺失的 key 列表。"""
    return [k for k in _REQUIRED_KEYS if k not in ctx.artifacts]


# ============================================================
# 主入口
# ============================================================

def execute(ctx: SkillContext) -> SkillResult:
    missing = _validate_artifacts(ctx)
    if missing:
        return SkillResult(
            outputs={
                "final_trade_decision": "",
                "risk_debate_state": ctx.artifacts.get("risk_debate_state", {}),
            },
            metadata={
                "agent": "portfolio_manager",
                "error": f"missing required artifacts: {missing}",
            },
        )

    # 延迟 import：避免 skills.core 加载时触发循环
    from valueagents.agents.managers.portfolio_manager import create_portfolio_manager

    # 1) memory：优先从 artifacts 拿真 memory，否则用空实现
    memory = ctx.artifacts.get("_portfolio_manager_memory")
    if memory is None:
        print("   [portfolio_manager_skill] _portfolio_manager_memory not provided; using _NullMemory")
        memory = _NullMemory()

    # 2) 构造 agent_node（ctx.llm 带 callbacks）
    agent_node = create_portfolio_manager(ctx.llm, memory)

    # 3) 单次调用（无 tool loop）
    #    必须传完整 state：agent_node 内部读 company_of_interest / 4 份 report /
    #    investment_plan / trader_investment_plan / risk_debate_state
    result_state = agent_node(dict(ctx.artifacts))

    # 4) 提取输出
    final_decision = _extract_text(result_state.get("final_trade_decision", ""))
    new_risk_state = result_state.get(
        "risk_debate_state",
        ctx.artifacts.get("risk_debate_state", {}),
    )

    # 5) 兜底：决策为空
    if not final_decision:
        print("   ⚠️ [portfolio_manager_skill] empty final_trade_decision returned")
        final_decision = "Final decision unavailable: portfolio manager produced empty output."

    return SkillResult(
        outputs={
            "final_trade_decision": final_decision,
            "risk_debate_state": new_risk_state,
            # ❌ 不返回 messages（老代码也不返回）
        },
        metadata={
            "agent": "portfolio_manager",
            "decision_length": len(final_decision),
            "risk_history_length": len(
                ctx.artifacts.get("risk_debate_state", {}).get("history", "")
            ),
        },
    )
