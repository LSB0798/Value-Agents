from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from valueagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_news_gnews,
    get_global_news_gnews,
)
from valueagents.dataflows.config import get_config


def create_gnews_analyst(llm):
    def gnews_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        # ===== 添加节点入口打印 =====
        print(f"\n{'='*60}")
        print(f"🌐 [GNEWS ANALYST] Analyzing {state['company_of_interest']} at {current_date}")
        # print(f"{'='*60}")
        # ===========================

        tools = [
            get_news_gnews,
            get_global_news_gnews,
            # 如果需要 RAG，可以添加 retrieve_news_wisdom
        ]

        # ===== 添加工具列表打印 =====
        print(f"   Tools: {', '.join([tool.name for tool in tools])}")
        # ===========================

        system_message = (
            "You are a news researcher tasked with analyzing recent news and trends over the past week. "
            "Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. "
            "Use the available tools: get_news_gnews(ticker, start_date, end_date) for company-specific news, "
            "and get_global_news_gnews(curr_date, look_back_days, limit) for broader macroeconomic news. "
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
            # ===== 如果只有工具调用，打印提示 =====
            print(f"   ⏳ Waiting for tool results...")
            # =================================
        
        print(f"[GNEWS ANALYST] Done.\n")

        # ===== 添加报告摘要打印 =====
        # print(f"   📄 Return (result: {result})")
        # print(f"   📄 Return (news_report: {report})")
        # ===========================

        # ===========================
        print(f"🌐 [GNEWS ANALYST] Analyzed‌ {state['company_of_interest']} at {current_date}")
        print(f"{'='*60}")
        # ===========================

        return {
            "messages": [result],
            "news_report": report,
        }

    return gnews_analyst_node