# valueagents/agents/analysts/alpha_news_analyst.py
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from valueagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_alpha_news,
    get_alpha_global_news
)
# from valueagents.agents.utils.alpha_news_data_tools import (
#     get_alpha_news,
#     get_alpha_global_news,
# )
from datetime import datetime, timedelta
from langchain_core.messages import SystemMessage, HumanMessage


def create_alpha_news_analyst(llm, llm_compress=None):
    def alpha_news_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        # ===== 添加节点入口打印 =====
        print(f"\n{'='*60}")
        print(f"🔵 [ALPHA NEWS ANALYST] Analyzing {state['company_of_interest']} at {current_date}")
        # print(f"{'='*60}")
        # ===========================

        tools = [
            get_alpha_news,
            get_alpha_global_news,
        ]

        # ===== 添加工具列表打印 =====
        print(f"   Tools: {', '.join([tool.name for tool in tools])}")
        # ===========================

        system_message = (
            "You are a news researcher tasked with analyzing recent news and sentiment trends using Alpha Vantage data. "
            "Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. "
            "Use the available tools: get_alpha_news(ticker, start_date, end_date) for company-specific news, "
            "and get_alpha_global_news(curr_date, look_back_days, limit) for broader macroeconomic news. "
            "Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points, organized and easy to read."""
            + get_language_instruction()
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

        # ===== 添加工具调用/结果打印 =====
        if result.tool_calls:
            print(f"   ⚙️ Tool calls: {[tc['name'] for tc in result.tool_calls]}")
        # ===============================

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

            # ===== 添加报告摘要打印 =====
            print(f"   📄 Report generated (length: {len(report)} chars)")
            summary = report[:200].replace('\n', ' ') + "..." if len(report) > 200 else report.replace('\n', ' ')
            print(f"   Summary: {summary}")
            # ===========================
        else:
            print(f"   ⏳ Waiting for tool results...")

        print(f"[ALPHA NEWS ANALYST] Done.\n")

        # ===== 添加报告摘要打印 =====
        print(f"   📄 Return (messages: {result})")
        print(f"   📄 Return (news_report: {report})")
        # ===========================

        # ===========================
        print(f"🔴 [ALPHA NEWS ANALYST] Analyzed‌ {state['company_of_interest']} at {current_date}")
        print(f"{'='*60}")
        # ===========================

        return {
            "messages": [result],
            "news_report": report,  # 复用 news_report 字段
        }

    return alpha_news_analyst_node

