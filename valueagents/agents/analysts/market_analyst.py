# ./valueagents/agents/analysts/market_analyst.py
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from valueagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_indicators,
    get_language_instruction,
    get_stock_data,
    retrieve_market_wisdom,
)
from valueagents.dataflows.config import get_config


def create_market_analyst(llm, llm_compress=None):
    def market_analyst_node(state):
        # ----- 入口打印 -----
        ticker = state["company_of_interest"]
        trade_date = state["trade_date"]
        print(f"\n{'='*60}")
        print(f"📈 [MARKET ANALYST] Analyzing {ticker} at {trade_date}")
        # print(f"{'='*60}")

        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_stock_data,
            get_indicators,
            # retrieve_market_wisdom,
        ]

        # 打印可用工具
        print(f"   Tools available: {', '.join([tool.name for tool in tools])}")

        system_message = (
            """You are a trading assistant tasked with analyzing financial markets. Your role is to select the **most relevant indicators** for a given market condition or trading strategy from the following list. The goal is to choose up to **8 indicators** that provide complementary insights without redundancy. Categories and each category's indicators are:

Moving Averages:
- close_50_sma: 50 SMA: A medium-term trend indicator. Usage: Identify trend direction and serve as dynamic support/resistance. Tips: It lags price; combine with faster indicators for timely signals.
- close_200_sma: 200 SMA: A long-term trend benchmark. Usage: Confirm overall market trend and identify golden/death cross setups. Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries.
- close_10_ema: 10 EMA: A responsive short-term average. Usage: Capture quick shifts in momentum and potential entry points. Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals.

MACD Related:
- macd: MACD: Computes momentum via differences of EMAs. Usage: Look for crossovers and divergence as signals of trend changes. Tips: Confirm with other indicators in low-volatility or sideways markets.
- macds: MACD Signal: An EMA smoothing of the MACD line. Usage: Use crossovers with the MACD line to trigger trades. Tips: Should be part of a broader strategy to avoid false positives.
- macdh: MACD Histogram: Shows the gap between the MACD line and its signal. Usage: Visualize momentum strength and spot divergence early. Tips: Can be volatile; complement with additional filters in fast-moving markets.

Momentum Indicators:
- rsi: RSI: Measures momentum to flag overbought/oversold conditions. Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis.

Volatility Indicators:
- boll: Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. Usage: Acts as a dynamic benchmark for price movement. Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals.
- boll_ub: Bollinger Upper Band: Typically 2 standard deviations above the middle line. Usage: Signals potential overbought conditions and breakout zones. Tips: Confirm signals with other tools; prices may ride the band in strong trends.
- boll_lb: Bollinger Lower Band: Typically 2 standard deviations below the middle line. Usage: Indicates potential oversold conditions. Tips: Use additional analysis to avoid false reversal signals.
- atr: ATR: Averages true range to measure volatility. Usage: Set stop-loss levels and adjust position sizes based on current market volatility. Tips: It's a reactive measure, so use it as part of a broader risk management strategy.

Volume-Based Indicators:
- vwma: VWMA: A moving average weighted by volume. Usage: Confirm trends by integrating price action with volume data. Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses.

- Select indicators that provide diverse and complementary information. Avoid redundancy (e.g., do not select both rsi and stochrsi). Also briefly explain why they are suitable for the given market context. When you tool call, please use the exact name of the indicators provided above as they are defined parameters, otherwise your call will fail. Please make sure to call get_stock_data first to retrieve the CSV that is needed to generate indicators. Then use get_indicators with the specific indicator names. Write a very detailed and nuanced report of the trends you observe. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."""
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
        # tools : [StructuredTool(name='get_stock_data', description='Retrieve stock price data (OHLCV) for a given ticker symbol.\nUses the configured core_stock_apis vendor.\nArgs:\n    symbol (str): Ticker symbol of the company, e.g. AAPL, TSM\n    start_date (str): Start date in yyyy-mm-dd format\n    end_date (str): End date in yyyy-mm-dd format\nReturns:\n str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.', args_schema=<class 'langchain_core.utils.pydantic.get_stock_data'>, func=<function get_stock_data at 0x7d70686f7600>), StructuredTool(name='get_indicators', description="Retrieve a single technical indicator for a given ticker symbol.\nUses the configured technical_indicators vendor.\nArgs:\n    symbol (str): Ticker symbol of the company, e.g. AAPL, TSM\n indicator (str): A single technical indicator name, e.g. 'rsi', 'macd'. Call this tool once per indicator.\n    curr_date (str): The current trading date you are trading on, YYYY-mm-dd\n    look_back_days (int): How many days to look back, default is 30\nReturns:\n    str: A formatted dataframe containing the technical indicators for the specified ticker symbol and indicator.", args_schema=<class 'langchain_core.utils.pydantic.get_indicators'>, func=<function get_indicators at 0x7d706bc214e0>)]

        """ 为什么需要 partial？
            - 提前绑定不变的值：system_message、current_date、instrument_context 在这个节点内是固定的，不会因调用而改变。将它们 partial 化后，后续 invoke 只需要传入动态部分（如 messages）。
            - 代码简洁：避免在每次 invoke 时重复传递相同的参数。
            - 性能：partial 返回的是新模板，内部已做优化，不会重复解析。"""
        prompt = prompt.partial(system_message=system_message) # 将系统指令长文本 system_message 固定到模板的 {system_message} 位置。此后不需要再传入 system_message。
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools])) # 将工具名称列表拼接成字符串，如 "get_stock_data, get_indicators"，固定到某个 {tool_names} 变量（尽管模板中未使用，可能用于别处或代码遗留）。
        prompt = prompt.partial(current_date=current_date) # current_date : 2025-01-01 将 current_date 固定到 {current_date}。
        prompt = prompt.partial(instrument_context=instrument_context) # 将 instrument_context 固定到 {instrument_context}。instrument_context : The instrument to analyze is `0700.HK`. Use this exact ticker in every tool call, report, and recommendation, preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`).

        chain = prompt | llm.bind_tools(tools)

        """ type of state["messages"] : <class 'list'>
        state["messages"] : [HumanMessage(content='0700.HK', additional_kwargs={}, response_metadata={}, id='f44b5f7b-49af-4288-8e45-91e6d3f69149')]
        
        messages 是通过 MessagesPlaceholder 注入的，且其他变量已被 partial 固定，所以只需要传入 messages 列表。
        LangChain 内部会将传入的消息列表自动映射到名为 "messages" 的占位符。 
        如果不使用 partial，则需要： result = chain.invoke({"messages": state["messages"], "system_message": system_message, "current_date": current_date, "instrument_context": instrument_context, "tool_names": "..."}) """
        
        # === 调试开始 ===
        result = chain.invoke(state["messages"])

        # ----- 工具调用或报告生成打印 -----
        if result.tool_calls:
            print(f"   ⚙️ Tool calls: {[tc['name'] for tc in result.tool_calls]}")
        else:
            report = result.content
            print(f"   📄 Report generated (length: {len(report)} chars)")
            # 打印前 200 字符摘要（去除换行）
            summary = report[:200].replace('\n', ' ') + "..."
            print(f"   Summary: {summary}")
        
        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        # ----- 出口打印 -----
        print(f"[MARKET ANALYST] Done.\n")

        # ===== 添加报告摘要打印 =====
        # print(f"   📄 Return (result: {result})")
        # print(f"   📄 Return (news_report: {report})")
        # ===========================

        # ===========================
        print(f"📈 [MARKET ANALYST] Analyzed‌ {ticker} at {trade_date}")
        print(f"{'='*60}")
        # ===========================
        
        return {
            "messages": [result],
            "market_report": report,
        }

    return market_analyst_node
