from langchain_core.tools import tool
from typing import Annotated
from valueagents.dataflows.interface import route_to_vendor
from .compress_utils import compress_text, estimate_word_count

# ======================================================================= #
import datetime
import os

LOG_FILE = "/data/lishuaibing/valueagents/ValueAgents/valueagents.log"

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
        "end_date": end_date
    })
    # ======================================

    # 获取原始数据
    raw_result = route_to_vendor("get_stock_data", symbol, start_date, end_date)
    # print('[Stock Data] raw_result : {}'.format(raw_result))
    
    # 压缩（max_words=200）
    word_count_raw_result = estimate_word_count(raw_result)
    compressed = compress_text(raw_result, 
                               max_words=max(60, int(word_count_raw_result * 0.5)),
                               role=f"stock price data for {symbol}")
    # print('def get_stock_data raw_result length : {}'.format(len(raw_result)))
    # print('def get_stock_data raw_result : {}'.format(raw_result))
    # print('def get_stock_data compressed length : {}'.format(len(compressed)))
    # print('def get_stock_data compressed : {}'.format(compressed))

    # print('[Stock Data] compressed : {}'.format(compressed))
    # print(f"   🔄 [Stock Data] Compressed: {len(raw_result)} chars → {len(compressed)} chars")
    return compressed
