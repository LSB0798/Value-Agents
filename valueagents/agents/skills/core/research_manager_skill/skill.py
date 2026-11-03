# valueagents/agents/skills/core/research_manager_skill/skill.py
"""
Research Manager Core Skill

把 valueagents.agents.managers.research_manager.create_research_manager
包装为 SkillContext -> SkillResult。

与 4 个 analyst skill 的差异：
  - 无 tool loop：单次 llm.invoke，直接调 agent_node
  - 需要 memory：从 ctx.artifacts 取，缺失时用 _NullMemory 兜底
  - 输出 2 个字段：investment_plan + investment_debate_state
  - 不返回 messages
"""

from valueagents.agents.skills.contract import SkillContext, SkillResult


# ============================================================
# 空 memory 兜底（第 1 期用，第 2 期换成真 memory 注入）
# ============================================================

class _NullMemory:
    """
    与 FinancialSituationMemory 接口兼容的空实现。
    第 1 期不验证 reflection，get_memories 返回空列表即可。
    """

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
    "investment_debate_state",
)


def _validate_artifacts(ctx: SkillContext) -> list[str]:
    """返回缺失的 key 列表（不含空串检查，空报告也算存在）。"""
    return [k for k in _REQUIRED_KEYS if k not in ctx.artifacts]


# ============================================================
# 主入口
# ============================================================

def execute(ctx: SkillContext) -> SkillResult:
    missing = _validate_artifacts(ctx)
    if missing:
        return SkillResult(
            outputs={
                "investment_plan": "",
                "investment_debate_state": ctx.artifacts.get("investment_debate_state", {}),
            },
            metadata={
                "agent": "research_manager",
                "error": f"missing required artifacts: {missing}",
            },
        )

    # 延迟 import：避免 skills.core 加载时触发循环
    from valueagents.agents.managers.research_manager import create_research_manager

    # 1) memory：优先从 artifacts 拿真 memory，否则用空实现
    memory = ctx.artifacts.get("_invest_judge_memory")
    if memory is None:
        print("   [research_manager_skill] _invest_judge_memory not provided; using _NullMemory")
        memory = _NullMemory()

    # 2) 构造 agent_node（ctx.llm 带 callbacks）
    agent_node = create_research_manager(ctx.llm, memory)

    # 3) 单次调用（无 tool loop）
    #    必须传完整 state：agent_node 内部读 company_of_interest / 4 份 report / investment_debate_state
    result_state = agent_node(dict(ctx.artifacts))

    # 4) 提取输出
    investment_plan = _extract_text(result_state.get("investment_plan", ""))
    new_debate_state = result_state.get(
        "investment_debate_state",
        ctx.artifacts.get("investment_debate_state", {}),
    )

    # 5) 兜底：投资计划为空
    if not investment_plan:
        print("   ⚠️ [research_manager_skill] empty investment_plan returned")
        investment_plan = "Investment plan unavailable: research manager produced empty output."

    return SkillResult(
        outputs={
            "investment_plan": investment_plan,
            "investment_debate_state": new_debate_state,
            # ❌ 不返回 messages（老代码也不返回）
        },
        metadata={
            "agent": "research_manager",
            "plan_length": len(investment_plan),
            "debate_history_length": len(
                ctx.artifacts.get("investment_debate_state", {}).get("history", "")
            ),
        },
    )
