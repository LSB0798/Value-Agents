# valueagents/agents/skills/core/fundamentals_analyst_skill/skill.py
"""
Fundamentals Analyst Core Skill

把 valueagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst
包装为 SkillContext -> SkillResult。

与前面 3 个 analyst skill 的差异：
  - agent 函数名：create_fundamentals_analyst
  - 输出字段：fundamentals_report
  - 工具：4 个（fundamentals / balance_sheet / cashflow / income_statement）
  - max_iter=6（LLM 一次返回 4 个 tool_call，正常 2-3 轮完成）
  - token_budget=4000（最小，4 个工具内部均有 compress）

⚠️ 特殊注意事项：
  4 个工具（get_fundamentals 等）内部都调用 compress(text, state=None)。
  当 state=None 时，context_compressor 使用模块级 _global_state，
  其 reset 由 create_fundamentals_analyst 内部的 reset_global_state 触发。
  tool loop 第 1 轮 reset，第 2+ 轮复用 —— 与 LangGraph ToolNode 行为一致。
  但**跨 skill 串行时**（如先跑 market 再跑 fundamentals），
  market 的 _global_state 会被 fundamentals 的 reset 覆盖 —— 这是预期的，
  因为每个 agent_node 开头都会 reset_global_state。
"""

from valueagents.agents.skills.contract import SkillContext, SkillResult
from valueagents.agents.skills.runtime import run_agent_with_tools, build_tool_map


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


def execute(ctx: SkillContext) -> SkillResult:
    # 延迟 import：避免 skills.core 加载时触发 agents.analysts 的循环 import
    from valueagents.agents.analysts.fundamentals_analyst import create_fundamentals_analyst

    # 1) 用 ctx.llm 构造 agent_node
    agent_node = create_fundamentals_analyst(ctx.llm)

    # 2) 工具映射（全集；本 agent 实际只用 4 个财务工具）
    tool_map = build_tool_map()

    # 3) 跑 tool loop
    #    正常轮数：
    #      第 1 轮：LLM 一次返回 4 个 tool_call（fundamentals + 3 张报表）
    #      第 2 轮：tool 结果 → 报告
    #    max_iter=6 留 4 轮余量应对 LLM 分多轮调用（如 2+2 拆开）
    final_msg, all_messages = run_agent_with_tools(
        agent_node=agent_node,
        ctx=ctx,
        tool_map=tool_map,
        max_iter=6,
    )

    # 4) 从最终消息取报告
    report = _extract_text(getattr(final_msg, "content", None))

    # 5) 兜底：max_iter 用尽仍带 tool_calls
    if getattr(final_msg, "tool_calls", None):
        print(f"   ⚠️ [fundamentals_analyst_skill] max_iter exhausted; "
              f"final message still has {len(final_msg.tool_calls)} tool_calls")
        if not report:
            report = "Fundamentals analysis incomplete: tool call loop hit max_iter without producing a final report."

    return SkillResult(
        outputs={
            "fundamentals_report": report,
            "messages": [final_msg],
        },
        metadata={
            "agent": "fundamentals_analyst",
            "report_length": len(report),
            "total_messages": len(all_messages),
        },
    )
