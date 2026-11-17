# ./valueagents/agents/analysts/fundamentals_analyst.py
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from valueagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
    get_language_instruction,
)
from valueagents.dataflows.config import get_config
from valueagents.agents.utils.context_compressor import reset_global_state, report_global_state
from valueagents.agents.utils.prompt_fragments import DATA_AVAILABILITY_PROTOCOL
from valueagents.evidence.extractors.fundamentals import extract_fundamentals_evidence


def create_fundamentals_analyst(llm, llm_compress=None):
    def fundamentals_analyst_node(state):
        reset_global_state(token_budget=4000, agent_name="fundamentals_analyst")
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        print(f"   Tools available: {', '.join([tool.name for tool in tools])}")

        system_message = (
            "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, and company financial history to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            + " Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, `get_cashflow`, and `get_income_statement` for specific financial statements."
            + get_language_instruction()
            + DATA_AVAILABILITY_PROTOCOL
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

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        print(f"[FUNDAMENTALS ANALYST] Done.\n")

        report_global_state("fundamentals_analyst")
        # 🆕 Phase 2 W1.6：并行产出 fundamentals_evidence
        fundamentals_evidence = {}
        if len(result.tool_calls) == 0 and report:
            try:
                bundle = extract_fundamentals_evidence(
                    ticker=state["company_of_interest"],
                    end_date=state["trade_date"],
                    fundamentals_report=report,
                    messages=state.get("messages", []),
                    llm=llm,
                )
                fundamentals_evidence = bundle.model_dump()
            except Exception as e:
                print(f"   ⚠️ [fundamentals_evidence] extractor failed: {type(e).__name__}: {e}")

        return {
            "messages": [result],
            "fundamentals_report": report,
            "fundamentals_evidence": fundamentals_evidence,   # 🆕
        }

    return fundamentals_analyst_node
