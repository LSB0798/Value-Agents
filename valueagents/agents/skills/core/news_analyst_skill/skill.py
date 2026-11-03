# valueagents/agents/skills/core/news_analyst_skill/skill.py
"""
News Analyst Core Skill

把 valueagents.agents.analysts.news_analyst.create_news_analyst
包装为 SkillContext -> SkillResult。

与 social_analyst_skill 的差异：
  - agent 函数名：create_news_analyst
  - 输出字段：news_report
  - 工具：get_news + get_global_news（2 个）
  - max_iter=6（2 轮 tool call，留 4 轮余量）
  - token_budget=25000（内部，新闻文本长）
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
    from valueagents.agents.analysts.news_analyst import create_news_analyst

    # 1) 用 ctx.llm 构造 agent_node
    agent_node = create_news_analyst(ctx.llm)

    # 2) 工具映射（全集；本 agent 实际只用 get_news + get_global_news）
    tool_map = build_tool_map()

    # 3) 跑 tool loop
    #    正常 3 轮：LLM 一次返回 2 个 tool_call → tool 结果 → 报告
    #    留 3 轮余量应对 LLM 分多轮调用
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
        print(f"   ⚠️ [news_analyst_skill] max_iter exhausted; "
              f"final message still has {len(final_msg.tool_calls)} tool_calls")
        if not report:
            report = "News analysis incomplete: tool call loop hit max_iter without producing a final report."

    return SkillResult(
        outputs={
            "news_report": report,
            "messages": [final_msg],
        },
        metadata={
            "agent": "news_analyst",
            "report_length": len(report),
            "total_messages": len(all_messages),
        },
    )
