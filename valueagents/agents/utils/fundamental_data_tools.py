# ./valueagents/agents/utils/fundamental_data_tools.py
from langchain_core.tools import tool
from typing import Annotated
from valueagents.dataflows.interface import route_to_vendor
from .compress_utils import compress_text, estimate_word_count


@tool
def get_fundamentals(
    ticker: Annotated[str, "ticker symbol"],
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
) -> str:
    """
    Retrieve comprehensive fundamental data for a given ticker symbol.
    Uses the configured fundamental_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing comprehensive fundamental data
    """
    # return route_to_vendor("get_fundamentals", ticker, curr_date)
    result = route_to_vendor("get_fundamentals", ticker, curr_date)
    # print('[Fundamentals] result : {}'.format(result))

    word_count_result = estimate_word_count(result)
    compressed = compress_text(result, 
                               max_words=max(60, int(word_count_result * 0.5)),
                               role=f"fundamental data for {ticker}")
    # print('def get_fundamentals result length : {}'.format(len(result)))
    # print('def get_fundamentals result : {}'.format(result))
    # print('def get_fundamentals compressed length : {}'.format(len(compressed)))
    # print('def get_fundamentals compressed : {}'.format(compressed))

    # print('[Fundamentals] compressed : {}'.format(compressed))
    # print(f"   🔄 [Fundamentals] Compressed: {len(result)} chars → {len(compressed)} chars")
    return compressed


@tool
def get_balance_sheet(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[str, "reporting frequency: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"] = None,
) -> str:
    """
    Retrieve balance sheet data for a given ticker symbol.
    Uses the configured fundamental_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly)
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing balance sheet data
    """
    # return route_to_vendor("get_balance_sheet", ticker, freq, curr_date)
    result = route_to_vendor("get_balance_sheet", ticker, freq, curr_date)
    # print('[Balance Sheet] result : {}'.format(result))

    word_count_result = estimate_word_count(result)
    compressed = compress_text(result, 
                               max_words=max(60, int(word_count_result * 0.5)),
                               role=f"balance sheet for {ticker}")
    # print('def get_balance_sheet result length : {}'.format(len(result)))
    # print('def get_balance_sheet result : {}'.format(result))
    # print('def get_balance_sheet compressed length : {}'.format(len(compressed)))
    # print('def get_balance_sheet compressed : {}'.format(compressed))

    # print('[Balance Sheet] compressed : {}'.format(compressed))
    # print(f"   🔄 [Balance Sheet] Compressed: {len(result)} chars → {len(compressed)} chars")
    return compressed


@tool
def get_cashflow(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[str, "reporting frequency: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"] = None,
) -> str:
    """
    Retrieve cash flow statement data for a given ticker symbol.
    Uses the configured fundamental_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly)
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing cash flow statement data
    """
    # return route_to_vendor("get_cashflow", ticker, freq, curr_date)
    result = route_to_vendor("get_cashflow", ticker, freq, curr_date)
    # print('[Cashflow] result : {}'.format(result))

    word_count_result = estimate_word_count(result)
    compressed = compress_text(result, 
                               max_words=max(60, int(word_count_result * 0.5)),
                               role=f"cash flow for {ticker}")
    # print('def get_cashflow result length : {}'.format(len(result)))
    # print('def get_cashflow result : {}'.format(result))
    # print('def get_cashflow compressed length : {}'.format(len(compressed)))
    # print('def get_cashflow compressed : {}'.format(compressed))

    # print('[Cashflow] compressed : {}'.format(compressed))
    # print(f"   🔄 [Cashflow] Compressed: {len(result)} chars → {len(compressed)} chars")
    return compressed


@tool
def get_income_statement(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[str, "reporting frequency: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"] = None,
) -> str:
    """
    Retrieve income statement data for a given ticker symbol.
    Uses the configured fundamental_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly)
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing income statement data
    """
    # return route_to_vendor("get_income_statement", ticker, freq, curr_date)
    result = route_to_vendor("get_income_statement", ticker, freq, curr_date)
    # print('[Income Statement] result : {}'.format(result))

    word_count_result = estimate_word_count(result)
    compressed = compress_text(result, 
                               max_words=max(60, int(word_count_result * 0.5)),
                               role=f"income statement for {ticker}")
    # print('def get_income_statement result length : {}'.format(len(result)))
    # print('def get_income_statement result : {}'.format(result))
    # print('def get_income_statement compressed length : {}'.format(len(compressed)))
    # print('def get_income_statement compressed : {}'.format(compressed))

    # print('[Income Statement] compressed : {}'.format(compressed))
    # print(f"   🔄 [Income Statement] Compressed: {len(result)} chars → {len(compressed)} chars")
    return compressed