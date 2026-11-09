# valueagents/agents/skills/core/market_analyst_skill/skill.py
"""
Market Analyst Core Skill

把 valueagents.agents.analysts.market_analyst.create_market_analyst 包装为
SkillContext -> SkillResult 的接口。

关键差异（对比老 graph 节点）：
  1. tool loop 由本文件负责（run_agent_with_tools），不再依赖 LangGraph ToolNode
  2. LLM 从 ctx.llm 取（带 callbacks，恢复 StatsCallbackHandler 统计）
  3. market_report 从 final_msg.content 取，而不是 agent_node 返回的 "market_report"
     （agent_node 在 tool_calls 未清空的轮次里，market_report 恒为 ""）
  4. messages 只回传最后一条，避免 LangGraph operator.add reducer 累积 tool 中间态
"""

from valueagents.agents.skills.contract import SkillContext, SkillResult
from valueagents.agents.skills.runtime import run_agent_with_tools, build_tool_map


# ============================================================
# 辅助：从 LLM 消息 content 提取纯文本
# ============================================================

def _extract_text(content) -> str:
    """
    兼容三种形态：
      - str            : 直接返回
      - list[dict]     : OpenAI responses / Anthropic blocks，拼 type=="text"
      - list[str]      : 直接拼
      - 其他           : str(content) 兜底
    """
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
# 主入口
# ============================================================

def execute(ctx: SkillContext) -> SkillResult:
    # 延迟 import：避免 skills.core 加载时触发 agents.analysts 的循环 import
    from valueagents.agents.analysts.market_analyst import create_market_analyst

    # 1) 用 ctx.llm 构造 agent_node（callbacks 已随 llm 传入）
    agent_node = create_market_analyst(ctx.llm)

    # 2) 工具映射（4 个 analyst 共享，build_tool_map 内部按需 import）
    tool_map = build_tool_map()

    # 3) 跑 tool loop
    #    max_iter=8：正常 3 轮即可（stock_data → 8×indicators → 报告），
    #    留 5 轮余量应对 LLM 分多轮调用工具
    final_msg, all_messages = run_agent_with_tools(
        agent_node=agent_node,
        ctx=ctx,
        tool_map=tool_map,
        max_iter=8,
    )

    # 4) 从最终消息取报告（不要用 agent_node 返回值里的 market_report 字段）
    report = _extract_text(getattr(final_msg, "content", None))

    # 5) 兜底：如果 final_msg 仍带 tool_calls（说明 max_iter 用尽），显式标注
    if getattr(final_msg, "tool_calls", None):
        print(f"   ⚠️ [market_analyst_skill] max_iter exhausted; "
              f"final message still has {len(final_msg.tool_calls)} tool_calls")
        if not report:
            report = "Market analysis incomplete: tool call loop hit max_iter without producing a final report."

    return SkillResult(
        outputs={
            "market_report": report,
            # 对齐老行为：只回传最终 AI 消息
            "messages": [final_msg],
        },
        metadata={
            "agent": "market_analyst",
            "report_length": len(report),
            "total_messages": len(all_messages),
        },
    )
