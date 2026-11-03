# ./valueagents/agents/analysts/news_analyst.py
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from typing import Annotated
from datetime import datetime
from valueagents.agents.utils.context_compressor import reset_global_state, report_global_state

from valueagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    retrieve_news_wisdom,   # 保留导入，未使用
)
from valueagents.agents.utils.news_aggregator import (
    aggregate_company_news,
    aggregate_global_news,
    render_news_for_llm,
)
from valueagents.agents.utils.news_cache_strategy import (
    compute_freshness,
    days_between,
)
from valueagents.agents.utils.news_dedup import dedup_and_rank
from valueagents.agents.src.data.cache import get_cache

from valueagents.agents.utils.news_aggregator_tools import (
    get_news,
    get_global_news,
)

# ===========================================================================
# 以下与原始实现完全一致（System Prompt、工具绑定、调用流程不变）
# ===========================================================================
def create_news_analyst(llm, llm_compress=None):
    def news_analyst_node(state):
        reset_global_state(token_budget=25000, agent_name="news_analyst")
        # ----- 入口打印 -----
        ticker = state["company_of_interest"]
        trade_date = state["trade_date"]
        print(f"\n{'='*60}")
        print(f"📰 [NEWS ANALYST] Analyzing {ticker} at {trade_date}")
        # print(f"{'='*60}")

        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_news,
            get_global_news,
        ]

        print(f"   Tools available: {', '.join([tool.name for tool in tools])}")

        system_message = (
            "You are a news researcher tasked with analyzing recent news and trends over the past week. Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. Use the available tools: get_news(query, start_date, end_date) for company-specific or targeted news searches, and get_global_news(curr_date, look_back_days, limit) for broader macroeconomic news. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
            + get_language_instruction()
            + "\n\nIMPORTANT: You MUST call each tool at most ONCE. Even if the returned news content appears empty, sparse, or not directly relevant to the ticker, you MUST proceed to write your final report based on whatever information you have. Do NOT call the same tool twice with different date ranges. Do NOT retry with a wider window. If data is insufficient, explicitly state 'insufficient data' in your report instead of retrying."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        if result.tool_calls:
            print(f"   ⚙️ Tool calls: {[tc['name'] for tc in result.tool_calls]}")
        else:
            report = result.content
            print(f"   📄 Report generated (length: {len(report)} chars)")
            summary = report[:200].replace('\n', ' ') + "..."
            print(f"   Summary: {summary}")

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        print(f"[NEWS ANALYST] Done.\n")

        print(f"📰 [NEWS ANALYST] Analyzed {ticker} at {trade_date}")
        print(f"{'='*60}")

        report_global_state("news_analyst")
        return {
            "messages": [result],
            "news_report": report,
        }

    return news_analyst_node