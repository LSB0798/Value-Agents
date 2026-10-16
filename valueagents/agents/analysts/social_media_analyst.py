# ./valueagents/agents/analysts/social_media_analyst.py
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from valueagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction, get_news
from valueagents.agents.utils.agent_utils import retrieve_sentiment_wisdom
from valueagents.dataflows.config import get_config


def create_social_media_analyst(llm, llm_compress=None):
    def social_media_analyst_node(state):
        # ----- 入口打印 -----
        ticker = state["company_of_interest"]
        trade_date = state["trade_date"]
        print(f"\n{'='*60}")
        print(f"📱 [SOCIAL ANALYST] Analyzing {ticker} at {trade_date}")
        # print(f"{'='*60}")

        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_news,
            # retrieve_sentiment_wisdom,
        ]

        print(f"   Tools available: {', '.join([tool.name for tool in tools])}")

        system_message = (
            "You are a social media and company specific news researcher/analyst tasked with analyzing social media posts, recent company news, and public sentiment for a specific company over the past week. You will be given a company's name your objective is to write a comprehensive long report detailing your analysis, insights, and implications for traders and investors on this company's current state after looking at social media and what people are saying about that company, analyzing sentiment data of what people feel each day about the company, and looking at recent company news. Use the get_news(query, start_date, end_date) tool to search for company-specific news and social media discussions. Try to look at all sources possible from social media to sentiment to news. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
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

        print(f"[SOCIAL ANALYST] Done.\n")

        print(f"📱 [SOCIAL ANALYST] Analyzed‌ {ticker} at {trade_date}")
        print(f"{'='*60}")
        
        return {
            "messages": [result],
            "sentiment_report": report,
        }

    return social_media_analyst_node
