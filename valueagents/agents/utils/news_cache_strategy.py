# valueagents/agents/utils/news_cache_strategy.py
"""
新闻缓存策略：判断缓存是否充分，决定直用/增量/全量。
纯函数模块，不读取/写入缓存，不调 API。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from valueagents.agents.utils.news_schema import NewsItem


@dataclass
class CacheFreshness:
    covered_days: int
    total_days: int
    item_count: int
    source_coverage: int
    expected_sources: int = 3
    expected_min_items: int = 5

    @property
    def time_coverage(self) -> float:
        return self.covered_days / self.total_days if self.total_days else 0.0

    @property
    def is_sufficient(self) -> bool:
        return (
            self.time_coverage >= 0.8
            and self.item_count >= self.expected_min_items
            and self.source_coverage >= 1
        )

    @property
    def decision(self) -> str:
        """返回 'use_cache' | 'fetch_all' | 'fetch_incremental'"""
        if self.is_sufficient:
            return "use_cache"
        if self.time_coverage < 0.3:
            return "fetch_all"
        return "fetch_incremental"


def _days_in_window(start: str, end: str) -> list[str]:
    try:
        s = datetime.strptime(start, "%Y-%m-%d")
        e = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        return []
    days = []
    cur = s
    while cur <= e:
        days.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return days


def compute_freshness(
    items: Iterable[NewsItem],
    start: str,
    end: str,
    expected_sources: int = 3,
) -> CacheFreshness:
    """计算缓存对请求窗口的充分性。"""
    window_days = _days_in_window(start, end)
    total_days = len(window_days)
    if total_days == 0:
        return CacheFreshness(0, 0, 0, 0, expected_sources)

    in_window = [it for it in items if start <= it.date <= end]
    covered = {it.date for it in in_window if it.date in window_days}
    providers = {it.provider for it in in_window if it.provider and it.provider != "unknown"}

    return CacheFreshness(
        covered_days=len(covered),
        total_days=total_days,
        item_count=len(in_window),
        source_coverage=len(providers),
        expected_sources=expected_sources,
    )


def find_missing_windows(
    items: Iterable[NewsItem],
    start: str,
    end: str,
    min_items_per_day: int = 1,
) -> list[tuple[str, str]]:
    """
    找出缓存未覆盖或覆盖不足的日期段。
    例：请求 10-01 ~ 10-08，缓存覆盖了 10-05 ~ 10-08，
        返回 [("2026-10-01", "2026-10-04")]
    """
    window_days = _days_in_window(start, end)
    if not window_days:
        return []

    day_counts: dict[str, int] = {}
    for it in items:
        if start <= it.date <= end:
            day_counts[it.date] = day_counts.get(it.date, 0) + 1

    missing_windows = []
    run_start = None
    prev_day = None
    for day in window_days:
        count = day_counts.get(day, 0)
        if count < min_items_per_day:
            if run_start is None:
                run_start = day
        else:
            if run_start is not None:
                missing_windows.append((run_start, prev_day))
                run_start = None
        prev_day = day
    if run_start is not None:
        missing_windows.append((run_start, window_days[-1]))

    # 合并相邻窗口（间隔 ≤ 1 天）
    if not missing_windows:
        return []
    missing_windows.sort()
    merged = [missing_windows[0]]
    for s, e in missing_windows[1:]:
        last_s, last_e = merged[-1]
        last_e_dt = datetime.strptime(last_e, "%Y-%m-%d")
        s_dt = datetime.strptime(s, "%Y-%m-%d")
        if (s_dt - last_e_dt).days <= 2:
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))
    return merged


def days_between(start: str, end: str) -> int:
    try:
        s = datetime.strptime(start, "%Y-%m-%d")
        e = datetime.strptime(end, "%Y-%m-%d")
        return max((e - s).days + 1, 1)
    except ValueError:
        return 7
