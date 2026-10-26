# ./valueagents/agents/utils/news_data_tools.py
from langchain_core.tools import tool
from typing import Annotated
from valueagents.dataflows.interface import route_to_vendor
from .compress_utils import estimate_word_count          # ← 不再 import compress_text
from .context_compressor import compress                  # ← 新增


@tool
def get_news(
    ticker: Annotated[str, "Ticker symbol"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    query_reason: Annotated[str, "Why this news is needed, e.g. 'assess catalysts and sentiment'"] = "general analysis",
) -> str:
    """
    Retrieve news data for a given ticker symbol.
    Uses the configured news_data vendor.
    Args:
        ticker (str): Ticker symbol
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
        query_reason (str): Why the analyst needs this news (used for context-aware compression)
    Returns:
        str: A formatted string containing news data
    """
    raw_result = route_to_vendor("get_news", ticker, start_date, end_date)

    # 检查是否包含了错误信息（保留原逻辑，因为 L1 门控只认 N/A/None/No data）
    if "Error fetching news" in raw_result or "curl:" in raw_result:
        print(f"[News] Raw result contains network error, returning empty.")
        raw_result = f"No news found for {ticker} between {start_date} and {end_date}."

    # ===== 4 层压缩器 =====
    word_count_raw_result = estimate_word_count(raw_result)
    compressed = compress(
        text=raw_result,
        role=f"news for {ticker}",
        max_words=max(60, int(word_count_raw_result * 0.5)),
        query_reason=query_reason,
        state=None,
    )

    # 只保留简洁的长度统计，删掉全文打印
    print(f"   [News] {len(raw_result)} chars → {len(compressed)} chars")
    return compressed


@tool
def get_global_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of articles to return"] = 5,
    query_reason: Annotated[str, "Why this macro news is needed, e.g. 'assess rate and macro backdrop'"] = "general analysis",
) -> str:
    """
    Retrieve global news data.
    Uses the configured news_data vendor.
    Args:
        curr_date (str): Current date in yyyy-mm-dd format
        look_back_days (int): Number of days to look back (default 7)
        limit (int): Maximum number of articles to return (default 5)
        query_reason (str): Why the analyst needs this macro news (used for context-aware compression)
    Returns:
        str: A formatted string containing global news data
    """
    raw_result = route_to_vendor("get_global_news", curr_date, look_back_days, limit)

    # ===== 4 层压缩器 =====
    word_count_raw_result = estimate_word_count(raw_result)
    compressed = compress(
        text=raw_result,
        role="global macroeconomic news",
        max_words=max(60, int(word_count_raw_result * 0.5)),
        query_reason=query_reason,
        state=None,
    )

    print(f"   [Global News] {len(raw_result)} chars → {len(compressed)} chars")
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
    # 不压缩：insider transactions 数据本身很小，压缩可能丢关键数字
    return route_to_vendor("get_insider_transactions", ticker)