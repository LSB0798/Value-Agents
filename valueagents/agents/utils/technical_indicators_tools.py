from langchain_core.tools import tool
from typing import Annotated
from valueagents.dataflows.interface import route_to_vendor
from .compress_utils import estimate_word_count          # ← 不再 import compress_text
from .context_compressor import compress                  # ← 新增

@tool
def get_indicators(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[str, "The current trading date you are trading on, YYYY-mm-dd"],
    look_back_days: Annotated[int, "how many days to look back"] = 30,
    query_reason: Annotated[str, "Why this indicator is needed, e.g. 'confirm trend direction'"] = "general analysis",
) -> str:
    """
    Retrieve a single technical indicator for a given ticker symbol.
    Uses the configured technical_indicators vendor.
    Args:
        symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
        indicator (str): A single technical indicator name, e.g. 'rsi', 'macd'. Call this tool once per indicator.
        curr_date (str): The current trading date you are trading on, YYYY-mm-dd
        look_back_days (int): How many days to look back, default is 30
        query_reason (str): Why the analyst needs this indicator (used for context-aware compression)
    Returns:
        str: A formatted dataframe containing the technical indicators for the specified ticker symbol and indicator.
    """
    # LLMs sometimes pass multiple indicators as a comma-separated string;
    # split and process each individually.
    indicators = [i.strip().lower() for i in indicator.split(",") if i.strip()]
    results = []
    for ind in indicators:
        try:
            results.append(route_to_vendor("get_indicators", symbol, ind, curr_date, look_back_days))
        except ValueError as e:
            results.append(str(e))

    raw_result = "\n\n".join(results)

    # ===== 4 层压缩器（L1 会拦截全 N/A 的无效数据） =====
    word_count_raw_result = estimate_word_count(raw_result)
    compressed = compress(
        text=raw_result,
        role=f"technical indicators for {symbol}",
        max_words=max(60, int(word_count_raw_result * 0.5)),
        query_reason=query_reason,
        state=None,
    )

    return compressed