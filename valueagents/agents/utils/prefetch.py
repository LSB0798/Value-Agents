# valueagents/agents/utils/prefetch.py
"""
Prefetch 共享数据源。

在 19 个大师 skill 被串行/并发调用前，一次性预取所有可能用到的数据，
写入磁盘+内存缓存，让后续 skill 全部 Cache HIT。

使用场景：
  - master_team_skill.execute() 开头
  - research_team_skill.execute() 开头

设计原则：
  - 幂等：同一 (ticker, end_date) 只做一次
  - 隔离：每个数据源独立 try/except，单点失败不影响其他
  - 串行：prefetch 阶段串行，避免打爆数据源
  - 精确覆盖：一次性取最大 limit，再写进所有可能的 cache key
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Optional


_prefetch_lock = threading.Lock()
_prefetch_done: set[str] = set()


def _ensure_start_date(end_date: str, days: int) -> str:
    try:
        dt = datetime.strptime(end_date, "%Y-%m-%d")
        return (dt - timedelta(days=days)).strftime("%Y-%m-%d")
    except Exception:
        return end_date


def prefetch_shared_data(
    ticker: str,
    end_date: str,
    api_key: Optional[str] = None,
) -> dict[str, str]:
    """串行预取 19 个大师 skill 会用到的所有数据源。

    幂等：同一 (ticker, end_date) 只做一次。

    Returns:
        dict[str, str]: 每个数据源的预取状态
    """
    key = f"{ticker}:{end_date}"
    with _prefetch_lock:
        if key in _prefetch_done:
            print(f"   [prefetch] {ticker}@{end_date} 已预取过，跳过")
            return {}
        _prefetch_done.add(key)

    print(f"\n   📦 [prefetch] 开始预取共享数据：{ticker} @ {end_date}")
    status: dict[str, str] = {}

    # ---- 延迟 import，避免循环依赖 ----
    from valueagents.agents.src.tools.api import (
        get_financial_metrics,
        search_line_items,
        _ALL_LINE_ITEM_FIELDS,
        get_prices,
        get_insider_trades,
        get_company_news,
        get_market_cap,
    )
    from valueagents.agents.src.data.cache import get_cache
    from valueagents.agents.utils.news_aggregator_tools import get_news as aggregated_get_news

    cache = get_cache()

    # ---- 1. financial_metrics (ttm) ----
    try:
        metrics_ttm = get_financial_metrics(
            ticker, end_date, period="ttm", limit=12, api_key=api_key
        )
        for limit in (5, 8, 10, 12):
            cache_key = f"financial_metrics_{ticker}_ttm_{end_date}_{limit}"
            cache.set_financial_metrics(
                cache_key, [m.model_dump() for m in metrics_ttm[:limit]]
            )
        status["financial_metrics_ttm"] = f"ok({len(metrics_ttm)} records)"
        print(f"   ✅ financial_metrics ttm: {len(metrics_ttm)} records → 写入 5/8/10/12 四个 key")
    except Exception as e:
        status["financial_metrics_ttm"] = f"error: {e}"
        print(f"   ⚠️ financial_metrics ttm failed: {e}")

    # ---- 2. financial_metrics (annual) ----
    try:
        metrics_annual = get_financial_metrics(
            ticker, end_date, period="annual", limit=10, api_key=api_key
        )
        for limit in (5, 10):
            cache_key = f"financial_metrics_{ticker}_annual_{end_date}_{limit}"
            cache.set_financial_metrics(
                cache_key, [m.model_dump() for m in metrics_annual[:limit]]
            )
        status["financial_metrics_annual"] = f"ok({len(metrics_annual)} records)"
        print(f"   ✅ financial_metrics annual: {len(metrics_annual)} records → 写入 5/10 两个 key")
    except Exception as e:
        status["financial_metrics_annual"] = f"error: {e}"
        print(f"   ⚠️ financial_metrics annual failed: {e}")

    # ---- 3. line_items (ttm + annual，全字段) ----
    try:
        search_line_items(
            ticker, _ALL_LINE_ITEM_FIELDS, end_date,
            period="ttm", limit=10, api_key=api_key
        )
        status["line_items_ttm"] = "ok"
        print(f"   ✅ line_items ttm: {len(_ALL_LINE_ITEM_FIELDS)} fields")

        search_line_items(
            ticker, _ALL_LINE_ITEM_FIELDS, end_date,
            period="annual", limit=10, api_key=api_key
        )
        status["line_items_annual"] = "ok"
        print(f"   ✅ line_items annual: {len(_ALL_LINE_ITEM_FIELDS)} fields")
    except Exception as e:
        status["line_items"] = f"error: {e}"
        print(f"   ⚠️ line_items failed: {e}")

    # ---- 4. prices (end_date - 365 ~ end_date) ----
    try:
        start_date = _ensure_start_date(end_date, 365)
        prices = get_prices(ticker, start_date, end_date, api_key=api_key)
        status["prices"] = f"ok({len(prices)} records)"
        print(f"   ✅ prices: {len(prices)} records ({start_date} ~ {end_date})")
    except Exception as e:
        status["prices"] = f"error: {e}"
        print(f"   ⚠️ prices failed: {e}")

    # ---- 5. insider_trades ----
    try:
        start_date = _ensure_start_date(end_date, 365)
        trades = get_insider_trades(
            ticker, end_date, start_date=start_date, limit=1000, api_key=api_key
        )
        status["insider_trades"] = f"ok({len(trades)} records)"
        print(f"   ✅ insider_trades: {len(trades)} records")
    except Exception as e:
        status["insider_trades"] = f"error: {e}"
        print(f"   ⚠️ insider_trades failed: {e}")

    # ---- 6. company_news ----
    try:
        start_date = _ensure_start_date(end_date, 30)
        news = get_company_news(
            ticker, end_date, start_date=start_date, limit=250, api_key=api_key
        )
        status["company_news"] = f"ok({len(news)} records)"
        print(f"   ✅ company_news: {len(news)} records")
    except Exception as e:
        status["company_news"] = f"error: {e}"
        print(f"   ⚠️ company_news failed: {e}")

    # ---- 7. aggregated_news (供 news_sentiment_analyst) ----
    try:
        start_date = _ensure_start_date(end_date, 7)
        aggregated_get_news.invoke({
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
        })
        status["aggregated_news"] = "ok"
        print(f"   ✅ aggregated_news: 7 天窗口")
    except Exception as e:
        status["aggregated_news"] = f"error: {e}"
        print(f"   ⚠️ aggregated_news failed: {e}")

    # ---- 8. market_cap ----
    try:
        mc = get_market_cap(ticker, end_date, api_key=api_key)
        if mc:
            status["market_cap"] = f"ok({mc:.0f})"
            print(f"   ✅ market_cap: {mc:.0f}")
        else:
            status["market_cap"] = "miss"
            print(f"   ⚠️ market_cap: None")
    except Exception as e:
        status["market_cap"] = f"error: {e}"
        print(f"   ⚠️ market_cap failed: {e}")

    # ---- 汇总 ----
    ok_count = sum(1 for v in status.values() if v.startswith("ok"))
    total = len(status)
    print(f"   📦 [prefetch] 完成：{ok_count}/{total} 个数据源成功\n")

    return status


def clear_prefetch_cache() -> None:
    """清空幂等缓存（仅用于测试）"""
    with _prefetch_lock:
        _prefetch_done.clear()
