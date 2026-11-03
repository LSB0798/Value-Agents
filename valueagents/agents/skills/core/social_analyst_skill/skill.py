# valueagents/agents/skills/core/social_analyst_skill/skill.py
"""
Social Analyst Core Skill

把 valueagents.agents.analysts.social_media_analyst.create_social_media_analyst
包装为 SkillContext -> SkillResult。

与 market_analyst_skill 的差异：
  - agent 函数名：create_social_media_analyst
  - 输出字段：sentiment_report
  - 工具：仅 get_news（build_tool_map 是全集，不影响）
  - max_iter 更小（仅 1 次 tool call，正常 2 轮完成）
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
    from valueagents.agents.analysts.social_media_analyst import create_social_media_analyst

    # 1) 用 ctx.llm 构造 agent_node
    agent_node = create_social_media_analyst(ctx.llm)

    # 2) 工具映射（全集，多余工具不影响）
    tool_map = build_tool_map()

    # 3) 跑 tool loop
    #    social 只调 1 次 get_news，正常 2 轮结束（tool_call → 报告）
    #    max_iter=4 足够，留 2 轮余量
    final_msg, all_messages = run_agent_with_tools(
        agent_node=agent_node,
        ctx=ctx,
        tool_map=tool_map,
        max_iter=4,
    )

    # 4) 从最终消息取报告
    report = _extract_text(getattr(final_msg, "content", None))

    # 5) 兜底：max_iter 用尽仍带 tool_calls
    if getattr(final_msg, "tool_calls", None):
        print(f"   ⚠️ [social_analyst_skill] max_iter exhausted; "
              f"final message still has {len(final_msg.tool_calls)} tool_calls")
        if not report:
            report = "Social analysis incomplete: tool call loop hit max_iter without producing a final report."

    return SkillResult(
        outputs={
            "sentiment_report": report,
            "messages": [final_msg],
        },
        metadata={
            "agent": "social_analyst",
            "report_length": len(report),
            "total_messages": len(all_messages),
        },
    )
