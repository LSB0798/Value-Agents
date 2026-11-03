# valueagents/agents/utils/process_local_news.py
"""
一次性脚本：清洗本地 news 缓存。
- 输入：{data_cache_dir}/news/{ticker}_news.json
- 输出：
    - 终端统计报告
    - 清洗后的文件：{ticker}_news_cleaned.json
- 不覆盖原文件。
"""

import json
import os
from collections import Counter

from valueagents.default_config import DEFAULT_CONFIG
from valueagents.agents.utils.news_schema import NewsItem, repair_date


# 写盘时排除的字段（只在内存里使用，不落盘）
_EXCLUDED_FIELDS = {"fetched_at"}


def _to_storable_dict(item: NewsItem) -> dict:
    """把 NewsItem 转为可落盘的 dict，剔除不需要持久化的字段。"""
    d = item.to_dict()
    for k in _EXCLUDED_FIELDS:
        d.pop(k, None)
    return d


def process_ticker(ticker: str):
    news_dir = os.path.join(DEFAULT_CONFIG["data_cache_dir"], "news")
    src = os.path.join(news_dir, f"{ticker}_news.json")
    dst = os.path.join(news_dir, f"{ticker}_news_cleaned.json")

    if not os.path.exists(src):
        print(f"[SKIP] {src} not found")
        return

    print("=" * 72)
    print(f"处理 {ticker}")
    print("=" * 72)

    with open(src, "r", encoding="utf-8") as f:
        raw = json.load(f)
    print(f"[1] 读入原始记录数：{len(raw)}")

    # -------- 日期修复 --------
    repaired = 0
    unrecoverable = 0
    items: list[NewsItem] = []
    bad_samples: list[dict] = []

    for r in raw:
        old_date = r.get("date") or ""
        new_date = repair_date(old_date)
        if new_date and new_date != old_date:
            repaired += 1
        elif not new_date:
            unrecoverable += 1
            if len(bad_samples) < 5:
                bad_samples.append({"title": r.get("title", "")[:80], "date": old_date})
            continue

        r2 = dict(r)
        r2["date"] = new_date
        try:
            items.append(NewsItem.from_dict(r2))
        except Exception as e:
            unrecoverable += 1
            if len(bad_samples) < 5:
                bad_samples.append({"title": r.get("title", "")[:80], "error": str(e)})

    print(f"[2] 日期修复成功：{repaired} 条")
    print(f"[3] 无法修复/无效：{unrecoverable} 条")
    if bad_samples:
        print("    示例：")
        for b in bad_samples:
            print(f"      - {b}")

    # -------- 去重 --------
    seen = set()
    deduped: list[NewsItem] = []
    for it in items:
        fp = it.fingerprint()
        if fp in seen:
            continue
        seen.add(fp)
        deduped.append(it)
    print(f"[4] 精确去重后：{len(deduped)} 条（去掉 {len(items) - len(deduped)} 条重复）")

    # -------- 排序（date 升序，越早越靠前）--------
    def sort_key(it: NewsItem):
        # 主键：date 升序；次键：source_tier 升序（同一天内可信度高的靠前）
        return (it.date, it.source_tier)

    deduped.sort(key=sort_key, reverse=False)
    print(f"[5] 排序完成（date asc, tier asc）")

    # -------- 统计 --------
    date_counter = Counter(it.date for it in deduped)
    source_counter = Counter(it.source for it in deduped)
    tier_counter = Counter(it.source_tier for it in deduped)
    provider_counter = Counter(it.provider for it in deduped)
    sentiment_counter = Counter(it.sentiment for it in deduped)

    print("\n[6] 日期分布（Top 10）：")
    for d, c in date_counter.most_common(10):
        print(f"    {d}: {c} 条")
    print(f"    覆盖日期总数：{len(date_counter)} 天")
    print(f"    平均每天：{len(deduped) / max(len(date_counter), 1):.1f} 条")

    print("\n[7] 来源分布（Top 10）：")
    for s, c in source_counter.most_common(10):
        print(f"    {s}: {c} 条")

    print("\n[8] Tier 分布：")
    for t in sorted(tier_counter):
        print(f"    Tier {t}: {tier_counter[t]} 条")

    print("\n[9] Provider 分布：")
    for p, c in provider_counter.most_common():
        print(f"    {p}: {c} 条")

    print("\n[10] 情绪分布：")
    for s, c in sentiment_counter.most_common():
        print(f"    {s}: {c} 条")

    # -------- 预览 --------
    print("\n[11] 最早 5 条：")
    for it in deduped[:5]:
        print(f"    [{it.date}] [T{it.source_tier}] {it.source} - {it.title[:70]}")

    print("\n[12] 最新 5 条：")
    for it in deduped[-5:]:
        print(f"    [{it.date}] [T{it.source_tier}] {it.source} - {it.title[:70]}")

    # -------- 写回（剔除 fetched_at）--------
    output = [_to_storable_dict(it) for it in deduped]
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[13] 已写出清洗后的文件：{dst}")
    print(f"     原始大小：{os.path.getsize(src)} bytes")
    print(f"     清洗后  ：{os.path.getsize(dst)} bytes")

    # 确认 fetched_at 已被剔除
    has_fetched = any("fetched_at" in rec for rec in output[:50])
    print(f"     fetched_at 存在：{has_fetched}  （期望：False）")


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    process_ticker(ticker)