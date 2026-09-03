from langchain_core.tools import tool
from typing import Annotated
from valueagents.dataflows.interface import route_to_vendor
from .compress_utils import compress_text, estimate_word_count

@tool
def get_indicators(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[str, "The current trading date you are trading on, YYYY-mm-dd"],
    look_back_days: Annotated[int, "how many days to look back"] = 30,
) -> str:
    """
    Retrieve a single technical indicator for a given ticker symbol.
    Uses the configured technical_indicators vendor.
    Args:
        symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
        indicator (str): A single technical indicator name, e.g. 'rsi', 'macd'. Call this tool once per indicator.
        curr_date (str): The current trading date you are trading on, YYYY-mm-dd
        look_back_days (int): How many days to look back, default is 30
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
    # print('[Indicators] raw_result : {}'.format(raw_result))
    
    # 压缩（max_words=150）
    word_count_raw_result = estimate_word_count(raw_result)
    compressed = compress_text(raw_result, 
                               max_words=max(60, int(word_count_raw_result * 0.5)), 
                               role=f"technical indicators for {symbol}")
    # print('def get_indicators raw_result length : {}'.format(len(raw_result)))
    # print('def get_indicators raw_result : {}'.format(raw_result))
    # print('def get_indicators compressed length : {}'.format(len(compressed)))
    # print('def get_indicators compressed : {}'.format(compressed))

    # print('[Indicators] compressed : {}'.format(compressed))
    # print(f"   🔄 [Indicators] Compressed: {len(raw_result)} chars → {len(compressed)} chars")
    return compressed
