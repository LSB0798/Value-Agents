# ValueAgents/valueagents/dataflows/stockstats_utils.py
import time
import logging

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError
from stockstats import wrap
from typing import Annotated
import os
from .config import get_config

logger = logging.getLogger(__name__)

def yf_retry(func, max_retries=3, base_delay=2.0):
    """Execute a yfinance call with exponential backoff on rate limits.

    yfinance raises YFRateLimitError on HTTP 429 responses but does not
    retry them internally. This wrapper adds retry logic specifically
    for rate limits. Other exceptions propagate immediately.
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except YFRateLimitError:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Yahoo Finance rate limited, retrying in {delay:.0f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                raise


def _clean_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize a stock DataFrame for stockstats: parse dates, drop invalid rows, fill price gaps."""
    # data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce", utc=True).dt.tz_localize(None)
    data = data.dropna(subset=["Date"])

    price_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in data.columns]
    data[price_cols] = data[price_cols].apply(pd.to_numeric, errors="coerce")
    data = data.dropna(subset=["Close"])
    data[price_cols] = data[price_cols].ffill().bfill()

    return data


def load_ohlcv(symbol: str, curr_date: str) -> pd.DataFrame:
    """Fetch OHLCV data with caching, filtered to prevent look-ahead bias.

    Cache key = (symbol, curr_date), fixed 5-year window ending at curr_date.
    Same curr_date always hits the same cache file — no daily churn.

    Guard against empty downloads (Yahoo 反爬 / 非交易日 / 盘中拉不到 today 数据):
      - yf.download 失败或返回空 → fallback 到 Ticker.history
      - 仍为空 → 返回空 df，**不写缓存**（防止 42 字节僵尸文件）
    """
    config = get_config()
    curr_date_dt = pd.to_datetime(curr_date)

    # 🆕 缓存键用 curr_date，不用 today
    start_dt = curr_date_dt - pd.DateOffset(years=5)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = curr_date_dt.strftime("%Y-%m-%d")

    os.makedirs(config["data_cache_dir"], exist_ok=True)
    data_file = os.path.join(
        config["data_cache_dir"],
        f"{symbol}-YFin-data-{start_str}-{end_str}.csv",
    )

    # 🆕 缓存命中判据：文件存在且 > 1KB（排除 42 字节空文件）
    if os.path.exists(data_file) and os.path.getsize(data_file) > 1024:
        try:
            data = pd.read_csv(data_file, on_bad_lines="skip")
            if not data.empty:
                data = _clean_dataframe(data)
                data = data[data["Date"] <= curr_date_dt]
                if not data.empty:
                    return data
        except Exception:
            pass
        logger.warning(f"[load_ohlcv] cache {data_file} unreadable/empty, re-downloading")

    # 🆕 下载：yf.download → fallback Ticker.history
    data = None
    try:
        data = yf_retry(lambda: yf.download(
            symbol,
            start=start_str,
            end=end_str,
            multi_level_index=False,
            progress=False,
            auto_adjust=True,
        ))
    except Exception as e:
        logger.warning(f"[load_ohlcv] yf.download({symbol}) failed: {e}")

    # fallback：Ticker.history（对 end=today 更宽容，会自动拉到最新可用日期）
    if data is None or data.empty:
        logger.info(f"[load_ohlcv] yf.download empty for {symbol} ({start_str}~{end_str}), falling back to Ticker.history")
        try:
            ticker = yf.Ticker(symbol)
            data = yf_retry(lambda: ticker.history(
                start=start_str,
                end=end_str,
                auto_adjust=True,
            ))
        except Exception as e:
            logger.error(f"[load_ohlcv] Ticker.history({symbol}) also failed: {e}")
            data = None

    # 🆕 仍为空：返回空 df，**不写缓存**
    if data is None or data.empty:
        logger.error(f"[load_ohlcv] no OHLCV for {symbol} ({start_str}~{end_str})")
        return pd.DataFrame()

    data = data.reset_index()
    data.to_csv(data_file, index=False)

    data = _clean_dataframe(data)
    data = data[data["Date"] <= curr_date_dt]
    return data


def filter_financials_by_date(data: pd.DataFrame, curr_date: str) -> pd.DataFrame:
    """Drop financial statement columns (fiscal period timestamps) after curr_date.

    yfinance financial statements use fiscal period end dates as columns.
    Columns after curr_date represent future data and are removed to
    prevent look-ahead bias.
    """
    if not curr_date or data.empty:
        return data
    cutoff = pd.Timestamp(curr_date)
    mask = pd.to_datetime(data.columns, errors="coerce") <= cutoff
    return data.loc[:, mask]


class StockstatsUtils:
    @staticmethod
    def get_stock_stats(
        symbol: Annotated[str, "ticker symbol for the company"],
        indicator: Annotated[
            str, "quantitative indicators based off of the stock data for the company"
        ],
        curr_date: Annotated[
            str, "curr date for retrieving stock price data, YYYY-mm-dd"
        ],
    ):
        data = load_ohlcv(symbol, curr_date)
        df = wrap(data)
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
        curr_date_str = pd.to_datetime(curr_date).strftime("%Y-%m-%d")

        df[indicator]  # trigger stockstats to calculate the indicator
        matching_rows = df[df["Date"].str.startswith(curr_date_str)]

        if not matching_rows.empty:
            indicator_value = matching_rows[indicator].values[0]
            return indicator_value
        else:
            return "N/A: Not a trading day (weekend or holiday)"
