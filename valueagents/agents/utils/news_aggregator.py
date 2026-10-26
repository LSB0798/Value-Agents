# valueagents/agents/utils/news_aggregator.py
"""
多源新闻聚合器。

职责：
  1. 并行调用 Finnhub / Alpha Vantage / GNews
  2. 归一化为 NewsItem
  3. 去重 + 可信度排序
  4. 返回干净的 NewsItem 列表 + 每个源的统计

设计原则：
  - 不读取/写入任何缓存
  - 不依赖 tool 层（避免循环依赖）
  - 单源失败不影响整体（容错）
  - 可配置数据源列表
  - 所有 API key 从环境变量读取
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Optional

import requests

from valueagents.agents.utils.news_schema import (
    NewsItem,
    from_alpha_vantage,
    from_finnhub,
    from_gnews,
    get_source_tier,
)
from valueagents.agents.utils.news_dedup import dedup_and_rank, summarize_dedup


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# API 配置（环境变量优先，保留原项目里的默认 key 作为 fallback）
# ---------------------------------------------------------------------------
FINNHUB_API_KEY = os.environ.get(
    "FINNHUB_API_KEY", "d8tr0gpr01qhcnk5oj3gd8tr0gpr01qhcnk5oj40"
)
ALPHA_VANTAGE_API_KEY = os.environ.get(
    "ALPHA_VANTAGE_API_KEY", "LEPNUFM9ZGGRXWDR"
)
GNEWS_API_KEY = os.environ.get(
    "GNEWS_API_KEY", "45b40e4ff3978c4df4945e5828cba917"
)

DEFAULT_SOURCES = ("finnhub", "alpha_vantage", "gnews")


# ---------------------------------------------------------------------------
# 统计结构
# ---------------------------------------------------------------------------
@dataclass
class SourceStats:
    name: str
    fetched: int = 0
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class AggregationResult:
    ticker: str
    items: list[NewsItem] = field(default_factory=list)
    source_stats: dict[str, SourceStats] = field(default_factory=dict)
    dedup_stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "items": [it.to_dict() for it in self.items],
            "source_stats": {
                k: {
                    "fetched": v.fetched,
                    "error": v.error,
                    "duration_ms": round(v.duration_ms, 1),
                }
                for k, v in self.source_stats.items()
            },
            "dedup_stats": self.dedup_stats,
        }


# ---------------------------------------------------------------------------
# 日期工具
# ---------------------------------------------------------------------------
def _compute_start_date(end_date: str, look_back_days: int) -> str:
    try:
        dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        dt = datetime.utcnow()
    return (dt - timedelta(days=look_back_days)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# 单源 fetcher（直接调底层 API，不走 tool 层）
# ---------------------------------------------------------------------------
def _fetch_finnhub(ticker: str, start_date: str, end_date: str, limit: int = 50) -> list[NewsItem]:
    """从 Finnhub 拉取公司新闻。"""
    if not FINNHUB_API_KEY:
        raise RuntimeError("FINNHUB_API_KEY not set")
    import finnhub
    client = finnhub.Client(api_key=FINNHUB_API_KEY)
    raw = client.company_news(ticker, _from=start_date, to=end_date) or []
    raw = raw[:limit]
    return [from_finnhub(item, ticker) for item in raw]


def _fetch_alpha_vantage(ticker: str, start_date: str, end_date: str, limit: int = 50) -> list[NewsItem]:
    """从 Alpha Vantage 拉取公司新闻（含情感标签）。"""
    if not ALPHA_VANTAGE_API_KEY:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY not set")
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "limit": min(limit, 50),
        "apikey": ALPHA_VANTAGE_API_KEY,
        "sort": "LATEST",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "Error Message" in data:
        raise RuntimeError(f"Alpha Vantage error: {data['Error Message']}")
    feed = data.get("feed", []) or []
    # 时间窗过滤（Alpha Vantage 的 limit 是全局的，可能带出窗口外的数据）
    items = [from_alpha_vantage(x, ticker) for x in feed]
    return [it for it in items if start_date <= it.date <= end_date][:limit]


def _fetch_gnews(ticker: str, start_date: str, end_date: str, limit: int = 10) -> list[NewsItem]:
    """从 GNews 拉取公司新闻。"""
    if not GNEWS_API_KEY:
        raise RuntimeError("GNEWS_API_KEY not set")
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": f'"{ticker}" stock',
        "apikey": GNEWS_API_KEY,
        "from": start_date,
        "to": end_date,
        "lang": "en",
        "sortby": "publishedAt",
        "max": min(limit, 10),
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    articles = data.get("articles", []) or []
    return [from_gnews(x, ticker) for x in articles]


_FETCHERS = {
    "finnhub": _fetch_finnhub,
    "alpha_vantage": _fetch_alpha_vantage,
    "gnews": _fetch_gnews,
}


# ---------------------------------------------------------------------------
# 单源包装（计时 + 错误捕获）
# ---------------------------------------------------------------------------
def _safe_fetch(
    source_name: str, ticker: str, start_date: str, end_date: str
) -> tuple[str, list[NewsItem], SourceStats]:
    stats = SourceStats(name=source_name)
    t0 = time.perf_counter()
    fetcher = _FETCHERS.get(source_name)
    if fetcher is None:
        stats.error = f"unknown source: {source_name}"
        stats.duration_ms = (time.perf_counter() - t0) * 1000
        return source_name, [], stats
    try:
        items = fetcher(ticker, start_date, end_date)
        stats.fetched = len(items)
        return source_name, items, stats
    except Exception as e:
        logger.warning("[news_aggregator] %s failed: %s", source_name, e)
        stats.error = str(e)
        return source_name, [], stats
    finally:
        stats.duration_ms = (time.perf_counter() - t0) * 1000


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def aggregate_company_news(
    ticker: str,
    end_date: str,
    look_back_days: int = 7,
    sources: Optional[Iterable[str]] = None,
    similarity_threshold: float = 0.75,
    date_tolerance_days: int = 1,
    max_workers: int = 3,
) -> AggregationResult:
    """
    并行拉取多家新闻 API，归一化、去重、排序。

    Args:
        ticker: 股票代码
        end_date: 截止日期 YYYY-MM-DD
        look_back_days: 向前回溯天数
        sources: 启用的源列表；默认三家全开
        similarity_threshold: 模糊去重阈值
        date_tolerance_days: 跨源日期容差
        max_workers: 并行线程数

    Returns:
        AggregationResult
    """
    source_list = list(sources) if sources else list(DEFAULT_SOURCES)
    start_date = _compute_start_date(end_date, look_back_days)

    result = AggregationResult(ticker=ticker)
    all_items: list[NewsItem] = []

    if not source_list:
        result.dedup_stats = summarize_dedup([], [])
        return result

    with ThreadPoolExecutor(max_workers=min(max_workers, len(source_list))) as pool:
        futures = {
            pool.submit(_safe_fetch, name, ticker, start_date, end_date): name
            for name in source_list
        }
        for fut in as_completed(futures):
            name, items, stats = fut.result()
            result.source_stats[name] = stats
            all_items.extend(items)

    # ★ 新增：统一窗口过滤（防止 Finnhub/GNews 忽略 from/to 而带出窗口外数据）
    before_filter = len(all_items)
    all_items = [it for it in all_items if start_date <= it.date <= end_date]
    filtered_out = before_filter - len(all_items)
    if filtered_out:
        logger.info(
            "[news_aggregator] %s: filtered out %d items outside [%s, %s]",
            ticker, filtered_out, start_date, end_date,
        )

    deduped = dedup_and_rank(
        all_items,
        similarity_threshold=similarity_threshold,
        date_tolerance_days=date_tolerance_days,
    )
    result.items = deduped
    result.dedup_stats = summarize_dedup(all_items, deduped)
    # 便于观察：把被窗口过滤掉的条数写进 stats
    result.dedup_stats["filtered_out_of_window"] = filtered_out

    logger.info(
        "[news_aggregator] %s: fetched=%d deduped=%d (ratio=%.2f)",
        ticker,
        len(all_items),
        len(deduped),
        result.dedup_stats.get("compression_ratio", 0.0),
    )
    return result


def aggregate_company_news_simple(
    ticker: str,
    end_date: str,
    look_back_days: int = 7,
) -> list[NewsItem]:
    """便捷入口：只返回 NewsItem 列表（丢弃 stats）。"""
    return aggregate_company_news(
        ticker=ticker, end_date=end_date, look_back_days=look_back_days
    ).items


# ---------------------------------------------------------------------------
# 渲染成 LLM 可读的 Markdown
# ---------------------------------------------------------------------------
def render_news_for_llm(
    items: list[NewsItem],
    max_items: int = 15,
    include_corroboration: bool = True,
) -> str:
    """
    把 NewsItem 列表渲染为 Markdown 文本，供 LLM 阅读。

    格式：
        1. [Reuters|T2] 2026-09-01 — Meta launches Muse AI agent
           摘要...
           https://...
        2. [Moomoo + 2 others|T4] 2026-08-30 — ...
    """
    lines: list[str] = []
    for idx, it in enumerate(items[:max_items], 1):
        sources = it.source
        if include_corroboration and it.corroborating_sources:
            sources = f"{it.source} + {len(it.corroborating_sources)} others"
        header = f"{idx}. [{sources}|T{it.source_tier}] {it.date} — {it.title}"
        lines.append(header)
        if it.summary:
            summary = it.summary.strip().replace("\n", " ")
            if len(summary) > 300:
                summary = summary[:297] + "..."
            lines.append(f"   {summary}")
        if it.url:
            lines.append(f"   {it.url}")
        lines.append("")
    return "\n".join(lines).strip()


# ===========================================================================
# 全球新闻聚合（Step 4 追加）
# ===========================================================================

def _fetch_finnhub_global(start_date: str, end_date: str, limit: int = 50) -> list[NewsItem]:
    """Finnhub general news（'general' 频道）。"""
    if not FINNHUB_API_KEY:
        raise RuntimeError("FINNHUB_API_KEY not set")
    import finnhub
    client = finnhub.Client(api_key=FINNHUB_API_KEY)
    raw = client.general_news("general", min_id=0) or []
    items: list[NewsItem] = []
    for item in raw[: limit * 2]:
        ts = item.get("datetime")
        date = (
            datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            if isinstance(ts, (int, float))
            else ""
        )
        if not date or not (start_date <= date <= end_date):
            continue
        source = item.get("source") or "finnhub"
        items.append(
            NewsItem(
                ticker="GLOBAL",
                date=date,
                title=item.get("headline") or "",
                summary=item.get("summary") or "",
                url=item.get("url") or "",
                source=source,
                source_tier=__import__(
                    "valueagents.agents.utils.news_schema",
                    fromlist=["get_source_tier"],
                ).get_source_tier(source),
                provider="finnhub",
            )
        )
        if len(items) >= limit:
            break
    return items


def _fetch_alpha_vantage_global(start_date: str, end_date: str, limit: int = 50) -> list[NewsItem]:
    """Alpha Vantage NEWS_SENTIMENT + 宏观 topics。"""
    if not ALPHA_VANTAGE_API_KEY:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY not set")
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "topics": "economy_macro,financial_markets",
        "limit": min(limit, 50),
        "apikey": ALPHA_VANTAGE_API_KEY,
        "sort": "LATEST",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "Error Message" in data:
        raise RuntimeError(f"Alpha Vantage error: {data['Error Message']}")
    feed = data.get("feed", []) or []
    items = [from_alpha_vantage(x, "GLOBAL") for x in feed]
    return [it for it in items if start_date <= it.date <= end_date][:limit]


def _fetch_gnews_global(start_date: str, end_date: str, limit: int = 20) -> list[NewsItem]:
    """GNews 用多个宏观关键词查询后去重。"""
    if not GNEWS_API_KEY:
        raise RuntimeError("GNEWS_API_KEY not set")
    url = "https://gnews.io/api/v4/search"
    queries = [
        "stock market economy",
        "Federal Reserve interest rates",
        "inflation economic outlook",
        "global markets trading",
    ]
    items: list[NewsItem] = []
    seen_titles: set[str] = set()
    for q in queries:
        params = {
            "q": q,
            "apikey": GNEWS_API_KEY,
            "from": start_date,
            "to": end_date,
            "lang": "en",
            "sortby": "relevance",
            "max": min(limit, 10),
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
        except Exception:
            continue
        for art in resp.json().get("articles", []) or []:
            title = art.get("title")
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            items.append(from_gnews(art, "GLOBAL"))
    return items[:limit]


_GLOBAL_FETCHERS = {
    "finnhub": _fetch_finnhub_global,
    "alpha_vantage": _fetch_alpha_vantage_global,
    "gnews": _fetch_gnews_global,
}


def _safe_fetch_global(
    source_name: str, start_date: str, end_date: str
) -> tuple[str, list[NewsItem], SourceStats]:
    stats = SourceStats(name=source_name)
    t0 = time.perf_counter()
    fetcher = _GLOBAL_FETCHERS.get(source_name)
    if fetcher is None:
        stats.error = f"unknown global source: {source_name}"
        stats.duration_ms = (time.perf_counter() - t0) * 1000
        return source_name, [], stats
    try:
        items = fetcher(start_date, end_date)
        stats.fetched = len(items)
        return source_name, items, stats
    except Exception as e:
        logger.warning("[news_aggregator:global] %s failed: %s", source_name, e)
        stats.error = str(e)
        return source_name, [], stats
    finally:
        stats.duration_ms = (time.perf_counter() - t0) * 1000


def aggregate_global_news(
    end_date: str,
    look_back_days: int = 7,
    sources: Optional[Iterable[str]] = None,
    similarity_threshold: float = 0.75,
    date_tolerance_days: int = 1,
    max_workers: int = 3,
) -> AggregationResult:
    """并行拉取多家全球新闻，归一化、去重、排序。"""
    source_list = list(sources) if sources else list(DEFAULT_SOURCES)
    start_date = _compute_start_date(end_date, look_back_days)

    result = AggregationResult(ticker="GLOBAL")
    all_items: list[NewsItem] = []

    if not source_list:
        result.dedup_stats = summarize_dedup([], [])
        return result

    with ThreadPoolExecutor(max_workers=min(max_workers, len(source_list))) as pool:
        futures = {
            pool.submit(_safe_fetch_global, name, start_date, end_date): name
            for name in source_list
        }
        for fut in as_completed(futures):
            name, items, stats = fut.result()
            result.source_stats[name] = stats
            all_items.extend(items)

    # ★ 新增：统一窗口过滤
    before_filter = len(all_items)
    all_items = [it for it in all_items if start_date <= it.date <= end_date]
    filtered_out = before_filter - len(all_items)
    if filtered_out:
        logger.info(
            "[news_aggregator:global] filtered out %d items outside [%s, %s]",
            filtered_out, start_date, end_date,
        )

    deduped = dedup_and_rank(
        all_items,
        similarity_threshold=similarity_threshold,
        date_tolerance_days=date_tolerance_days,
    )
    result.items = deduped
    result.dedup_stats = summarize_dedup(all_items, deduped)
    result.dedup_stats["filtered_out_of_window"] = filtered_out
    return result
