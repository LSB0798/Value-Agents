# ./valueagents/agents/skills/runtime.py
from langchain_core.messages import ToolMessage, HumanMessage

def run_agent_with_tools(agent_node, ctx, tool_map: dict, max_iter: int = 8):
    """
    agent_node: callable(state: dict) -> dict，返回 {"messages": [...], ...}
    ctx: SkillContext
    返回: (final_message, all_messages)
    """
    messages = [HumanMessage(content=ctx.ticker)]
    for _ in range(max_iter):
        state = {**ctx.artifacts, "messages": messages}
        result = agent_node(state)
        last = result["messages"][-1]
        messages.append(last)
        if not getattr(last, "tool_calls", None):
            return last, messages
        for tc in last.tool_calls:
            tool = tool_map.get(tc["name"])
            if tool is None:
                content = f"Error: tool '{tc['name']}' not found"
            else:
                try:
                    content = tool.invoke(tc["args"])
                except Exception as e:
                    content = f"Error: {e}"
            messages.append(ToolMessage(content=str(content), tool_call_id=tc["id"]))
    # 超过 max_iter，返回最后一条
    return messages[-1], messages

def build_tool_map():
    """🆕 4 个 analyst 用到的全部工具"""
    from valueagents.agents.utils.agent_utils import (
        get_stock_data, get_indicators,
        get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement,
        get_insider_transactions,
    )
    from valueagents.agents.utils.news_aggregator_tools import get_news, get_global_news
    tools = [
        get_stock_data, get_indicators,
        get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement,
        get_news, get_global_news, get_insider_transactions,
    ]
    return {t.name: t for t in tools}


# 文件末尾追加
import contextvars

_current_llm: contextvars.ContextVar = contextvars.ContextVar("current_llm", default=None)


def set_current_llm(llm):
    """
    在 skill 调用前设置当前 LLM。
    返回 token，供 reset_current_llm 复位（finally 里调，避免污染）。
    """
    return _current_llm.set(llm)


def reset_current_llm(token):
    """恢复设置前的值。"""
    _current_llm.reset(token)


def get_current_llm():
    """call_llm 内部用这个取 LLM。无设置时返回 None。"""
    return _current_llm.get()