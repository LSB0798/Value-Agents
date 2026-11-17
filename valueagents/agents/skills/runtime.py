# ./valueagents/agents/skills/runtime.py
from langchain_core.messages import ToolMessage, HumanMessage
from valueagents.agents.utils.news_aggregator_tools import get_aggregated_news as get_news
from valueagents.agents.utils.news_aggregator_tools import get_aggregated_global_news as get_global_news

def run_agent_with_tools(
    agent_node,
    ctx,
    tool_map: dict,
    max_iter: int = 8,
    collect_extra: bool = False,
):
    messages = [HumanMessage(content=ctx.ticker)]
    extra_outputs: dict = {}

    for _ in range(max_iter):
        state = {**ctx.artifacts, "messages": messages}
        result = agent_node(state)
        last = result["messages"][-1]
        messages.append(last)

        # 🆕 累积 result 里除 messages 外的字段（后面会覆盖前面的）
        if collect_extra:
            for k, v in result.items():
                if k != "messages" and v:
                    extra_outputs[k] = v

        if not getattr(last, "tool_calls", None):
            if collect_extra:
                return last, messages, extra_outputs
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

    if collect_extra:
        return messages[-1], messages, extra_outputs
    return messages[-1], messages

def _validate_tool_names(tool_map: dict) -> None:
    """启动时校验所有 core skill 声明的 tool name 是否在 tool_map 里。"""
    import warnings
    # 每个 core skill 的 tool 声明（从代码里读，不改 skill 本身）
    expected = {
        "market_analyst": ["get_stock_data", "get_indicators"],
        "social_analyst": ["get_aggregated_news"],
        "news_analyst": ["get_aggregated_news", "get_aggregated_global_news"],
        "fundamentals_analyst": ["get_fundamentals", "get_balance_sheet",
                                  "get_cashflow", "get_income_statement"],
    }
    missing = set()
    for skill, names in expected.items():
        for n in names:
            if n not in tool_map:
                missing.add(f"{skill}:{n}")
    if missing:
        warnings.warn(
            f"[tool_map] 以下 tool name 在 skill 里声明但不在 tool_map 里: {missing}. "
            f"运行时 LLM 会收到 'tool not found'。请检查 skill 的 import。",
            RuntimeWarning,
        )

def build_tool_map():
    """🆕 4 个 analyst 用到的全部工具"""
    from valueagents.agents.utils.agent_utils import (
        get_stock_data, get_indicators,
        get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement,
        get_insider_transactions,
    )
    from valueagents.agents.utils.news_aggregator_tools import (
        get_aggregated_news, get_aggregated_global_news,
    )
    tools = [
        get_stock_data, get_indicators,
        get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement,
        get_aggregated_news, get_aggregated_global_news,
        get_insider_transactions,
    ]
    tool_map = {t.name: t for t in tools}

    _validate_tool_names(tool_map)
    return tool_map


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