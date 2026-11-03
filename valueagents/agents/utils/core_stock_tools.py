# ./valueagents/agents/utils/core_stock_tools.py
from langchain_core.tools import tool
from typing import Annotated
from valueagents.dataflows.interface import route_to_vendor
from .compress_utils import estimate_word_count
from .context_compressor import compress

# ======================================================================= #
import datetime
import os

LOG_FILE = "valueagents.log"

def debug_log(label, data):
    """Write debug info to a persistent log file."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{timestamp}] {label}\n")
        f.write(f"{'='*60}\n")
        if isinstance(data, dict):
            for k, v in data.items():
                v_str = str(v)[:500] if v is not None else "None"
                f.write(f"  {k}: {v_str}\n")
        else:
            f.write(f"  {str(data)[:2000]}\n")
        f.write("\n")

# 新增：同时输出到终端和日志的辅助函数
def log_print(label, message="", data=None):
    """同时打印到终端和写入日志文件"""
    # 终端输出（可能被Rich覆盖，但保留）
    print(f"\n[{label}] {message}")
    
    # 写入日志文件
    log_data = {"message": message}
    if data is not None:
        log_data.update(data)
    debug_log(label, log_data)

# ======================================================================= #


@tool
def get_stock_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    query_reason: Annotated[str, "Why this data is needed, e.g. 'assess trend near 200-SMA'"] = "general analysis",
) -> str:
    """
    Retrieve stock price data (OHLCV) for a given ticker symbol.
    Uses the configured core_stock_apis vendor.
    Args:
        symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
    """
    # RUN THIS WAY

    # ===== 使用 log_print 替代 print =====
    log_print("TOOL CALL", "get_stock_data invoked", {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "query_reason": query_reason,
    })
    # ======================================

    # 获取原始数据
    raw_result = route_to_vendor("get_stock_data", symbol, start_date, end_date)
    
    # 压缩（max_words=200）
    word_count_raw_result = estimate_word_count(raw_result)
    compressed = compress(
        text=raw_result,
        role=f"stock price data for {symbol}",
        max_words=max(60, int(word_count_raw_result * 0.5)),
        query_reason=query_reason,
        state=None,
    )
    return compressed
