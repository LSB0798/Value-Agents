# valueagents/agents/utils/news_aggregator_tools.py
"""
多源聚合新闻的 LangChain 工具封装。

对外只暴露两个 @tool：
  - get_aggregated_company_news(ticker, start_date, end_date) -> str
  - get_aggregated_global_news(curr_date, look_back_days, limit) -> str

设计原则：
  - 返回字符串（Markdown），与现有 get_news / get_global_news 等保持一致
  - 参数签名与现有工具一致，便于 Step 6 无痛替换
  - 不读取/写入任何缓存
  - 不改变任何现有链路行为
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import tool

from valueagents.agents.utils.news_aggregator import (
    aggregate_company_news,
    aggregate_global_news,
    render_news_for_llm,
)


@tool
def get_news( # ← 原 get_aggregated_company_news
    ticker: Annotated[str, "Ticker symbol, e.g. AAPL, META"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve deduplicated company news from multiple sources (Finnhub, Alpha Vantage, GNews).

    This tool:
      - fetches company-specific news from multiple providers in parallel
      - normalizes all providers into a single schema
      - removes duplicates (exact title match + fuzzy title similarity within +/-1 day)
      - merges corroborating sources into a single event
      - ranks events by (date desc, source credibility asc, source_count desc)

    Each returned line is annotated with:
      - the leading source and its credibility tier (T1 highest .. T4 lowest)
      - the number of corroborating sources
      - the publication date and headline

    Use this tool whenever you need a clean, non-redundant view of company-specific news.
    """
    try:
        result = aggregate_company_news(
            ticker=ticker,
            end_date=end_date,
            look_back_days=_days_between(start_date, end_date),
        )
        if not result.items:
            return (
                f"No aggregated news found for {ticker} "
                f"between {start_date} and {end_date}."
            )
        stats_line = _format_stats_line(result)
        body = render_news_for_llm(result.items, max_items=20)
        return f"{stats_line}\n\n{body}"
    except Exception as e:
        return f"Error aggregating news for {ticker}: {e}"


@tool
def get_global_news( # ← 原 get_aggregated_global_news
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of events to return"] = 15,
) -> str:
    """
    Retrieve deduplicated global / macroeconomic news from multiple sources
    (Finnhub general, Alpha Vantage macro topics, GNews macro queries).

    Deduplication and ranking follow the same rules as company news:
      - exact + fuzzy dedup
      - rank by (date desc, source credibility asc, source_count desc)

    Use this tool for macro context: Fed policy, inflation, geopolitics, sector-wide events.
    """
    try:
        result = aggregate_global_news(
            end_date=curr_date,
            look_back_days=look_back_days,
        )
        if not result.items:
            return f"No aggregated global news found for {curr_date}."
        stats_line = _format_stats_line(result)
        body = render_news_for_llm(result.items, max_items=limit)
        return f"{stats_line}\n\n{body}"
    except Exception as e:
        return f"Error aggregating global news for {curr_date}: {e}"


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------
def _days_between(start_date: str, end_date: str) -> int:
    from datetime import datetime

    try:
        s = datetime.strptime(start_date, "%Y-%m-%d")
        e = datetime.strptime(end_date, "%Y-%m-%d")
        return max((e - s).days, 1)
    except Exception:
        return 7


def _format_stats_line(result) -> str:
    """生成一行统计，方便 LLM 判断数据质量。"""
    parts = []
    for name, s in result.source_stats.items():
        if s.error:
            parts.append(f"{name}=ERR")
        else:
            parts.append(f"{name}={s.fetched}")
    dedup = result.dedup_stats or {}
    head = " | ".join(parts) if parts else "no sources"
    return (
        f"[aggregated] sources: {head} | "
        f"raw={dedup.get('before', 0)} "
        f"deduped={dedup.get('after', 0)} "
        f"multi_source={dedup.get('multi_source_events', 0)}"
    )


# __all__ = ["get_aggregated_company_news", "get_aggregated_global_news"]
__all__ = ["get_news", "get_global_news"]