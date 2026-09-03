from langchain_core.tools import tool
from typing import Annotated
from valueagents.dataflows.interface import route_to_vendor
from .compress_utils import compress_text, estimate_word_count

@tool
def get_news(
    ticker: Annotated[str, "Ticker symbol"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve news data for a given ticker symbol.
    Uses the configured news_data vendor.
    Args:
        ticker (str): Ticker symbol
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: A formatted string containing news data
    """
    raw_result = route_to_vendor("get_news", ticker, start_date, end_date)
    # print('[News] raw_result : {}'.format(raw_result))
    # 压缩
    word_count_raw_result = estimate_word_count(raw_result)
    compressed = compress_text(raw_result, 
                               max_words=max(60, int(word_count_raw_result * 0.5)), 
                               role=f"news for {ticker}")
    # print('def get_news raw_result length : {}'.format(len(raw_result)))
    # print('def get_news raw_result : {}'.format(raw_result))
    # print('def get_news compressed length : {}'.format(len(compressed)))
    # print('def get_news compressed : {}'.format(compressed))

    # print('[News] compressed : {}'.format(compressed))
    # print(f"   🔄 [News] Compressed: {len(raw_result)} chars → {len(compressed)} chars")
    return compressed


@tool
def get_global_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of articles to return"] = 5,
) -> str:
    """
    Retrieve global news data.
    Uses the configured news_data vendor.
    Args:
        curr_date (str): Current date in yyyy-mm-dd format
        look_back_days (int): Number of days to look back (default 7)
        limit (int): Maximum number of articles to return (default 5)
    Returns:
        str: A formatted string containing global news data
    """
    raw_result = route_to_vendor("get_global_news", curr_date, look_back_days, limit)
    # print('[Global News] raw_result : {}'.format(raw_result))

    word_count_raw_result = estimate_word_count(raw_result)
    compressed = compress_text(raw_result, 
                               max_words=max(60, int(word_count_raw_result * 0.5)), 
                               role="global macroeconomic news")
    # print('def get_global_news raw_text length : {}'.format(len(raw_result)))
    # print('def get_global_news raw_text : {}'.format(raw_result))
    # print('def get_global_news compressed length : {}'.format(len(compressed)))
    # print('def get_global_news compressed : {}'.format(compressed))

    # print('[Global News] compressed : {}'.format(compressed))
    # print(f"   🔄 [Global News] Compressed: {len(raw_result)} chars → {len(compressed)} chars")
    return compressed


@tool
def get_insider_transactions(
    ticker: Annotated[str, "ticker symbol"],
) -> str:
    """
    Retrieve insider transaction information about a company.
    Uses the configured news_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
    Returns:
        str: A report of insider transaction data
    """
    return route_to_vendor("get_insider_transactions", ticker)
