# valueagents/agents/utils/news_dedup.py
"""
新闻去重与可信度排序。

职责：
  1. 精确去重：基于 NewsItem.fingerprint()
  2. 模糊去重：同一天内标题相似度 > 阈值视为同一事件，合并
  3. 可信度排序：date desc → source_tier asc → source_count desc

设计原则：
  - 不读取/写入任何缓存
  - 不调用任何外部 API
  - 纯函数，输入 list[NewsItem | dict]，输出 list[NewsItem]
  - 可独立单元测试
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Iterable, Sequence

from valueagents.agents.utils.news_schema import NewsItem, get_source_tier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 字符串相似度
# ---------------------------------------------------------------------------
_STOPWORDS = {
    "a", "an", "the", "of", "for", "in", "on", "to", "and", "or",
    "is", "are", "was", "were", "be", "been", "being",
    "with", "by", "from", "at", "as", "it", "its",
}


def _normalize_title(title: str) -> str:
    t = (title or "").lower()
    # ★ 新增：数字/缩写规范化
    t = re.sub(r"\$?\s*(\d+(?:\.\d+)?)\s*(million|m)\b", r"\1m", t)
    t = re.sub(r"\$?\s*(\d+(?:\.\d+)?)\s*(billion|b)\b", r"\1b", t)
    t = re.sub(r"\$?\s*(\d+(?:\.\d+)?)\s*(thousand|k)\b", r"\1k", t)
    t = re.sub(r"(\d),(\d{3})\b", r"\1\2", t)
    # 原有逻辑
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    tokens = [w for w in t.split() if w and w not in _STOPWORDS]
    return " ".join(tokens)


def _char_ngrams(text: str, n: int = 3) -> set[str]:
    """字符 n-gram 集合。对短标题效果好，不依赖分词。"""
    if len(text) < n:
        return {text} if text else set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _trigram_similarity(title1: str, title2: str) -> float:
    """
    标题相似度，返回 [0, 1]。

    规则（按优先级）：
      1. 规范化后为空 → 0
      2. 一条是另一条的子串（长度 >= 10）→ 1.0
      3. 否则用字符 trigram Jaccard
    """
    n1 = _normalize_title(title1)
    n2 = _normalize_title(title2)
    if not n1 or not n2:
        return 0.0

    # 子串加速：短标题是长标题的子串
    shorter, longer = (n1, n2) if len(n1) <= len(n2) else (n2, n1)
    if len(shorter) >= 10 and shorter in longer:
        return 1.0

    return _jaccard(_char_ngrams(n1), _char_ngrams(n2))


def title_similarity(title1: str, title2: str) -> float:
    """
    标题相似度，返回 [0, 1]。
    优先用语义嵌入（vLLM Qwen3-Embedding）；不可用时降级到字符 trigram。
    """
    # 局部导入，避免顶层循环依赖
    from valueagents.agents.utils import news_embedding

    sim = news_embedding.title_similarity_semantic(title1, title2)
    if sim is not None:
        return sim
    return _trigram_similarity(title1, title2)


# ---------------------------------------------------------------------------
# 输入归一化
# ---------------------------------------------------------------------------
def _coerce_to_item(x) -> NewsItem:
    if isinstance(x, NewsItem):
        return x
    if isinstance(x, dict):
        return NewsItem.from_dict(x)
    raise TypeError(f"Expected NewsItem or dict, got {type(x).__name__}")


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(date_str[: len(fmt.replace("%Y", "0000"))], fmt)
        except ValueError:
            continue
    return None


def _dates_close(d1: str, d2: str, tolerance_days: int = 1) -> bool:
    """跨供应商时区处理可能差 1 天，允许 1 天容差。"""
    if d1 == d2:
        return True
    dt1, dt2 = _parse_date(d1), _parse_date(d2)
    if not dt1 or not dt2:
        return False
    return abs((dt1 - dt2).days) <= tolerance_days


# ---------------------------------------------------------------------------
# 合并逻辑
# ---------------------------------------------------------------------------
def _merge_group(group: list[NewsItem]) -> NewsItem:
    """
    把一组视为同一事件的 NewsItem 合并为一条。

    - 主条目：source_tier 最小（最可信）的那条；tier 相同时选 summary 最长的
    - corroborating_sources：其他所有来源的去重列表
    - source_count：主条目 + corroborating 的数量
    - sentiment：取主条目的；如果主条目为 unknown，用组内出现最多的非 unknown
    """
    if len(group) == 1:
        return group[0]

    def sort_key(it: NewsItem):
        return (it.source_tier, -len(it.summary or ""), it.date)

    ordered = sorted(group, key=sort_key)
    primary = ordered[0]

    # 来源归并
    other_sources: list[str] = []
    seen: set[str] = set()
    for it in ordered[1:]:
        s = (it.source or "unknown").strip()
        if s and s not in seen:
            seen.add(s)
            other_sources.append(s)

    # sentiment 补齐
    sentiment = primary.sentiment
    if sentiment == "unknown":
        counts = {"bullish": 0, "bearish": 0, "neutral": 0}
        for it in ordered:
            if it.sentiment in counts:
                counts[it.sentiment] += 1
        best = max(counts, key=counts.get)
        if counts[best] > 0:
            sentiment = best  # type: ignore[assignment]

    return primary.model_copy(
        update={
            "corroborating_sources": other_sources,
            "source_count": len(ordered),
            "sentiment": sentiment,
        }
    )


# ---------------------------------------------------------------------------
# 主接口
# ---------------------------------------------------------------------------
def dedup_news(
    items: Iterable[NewsItem | dict],
    similarity_threshold: float = 0.75,
    date_tolerance_days: int = 1,
) -> list[NewsItem]:
    """
    三阶段去重。

    阶段 1（精确）：按 fingerprint 去重（同标题保留 tier 最高的）
    阶段 2（模糊）：同一天内、标题相似度 >= 阈值视为同一事件，union-find 合并
    阶段 3（校验）：每个簇内，与 anchor 相似度不足的成员被踢出，防止链式合并
    """
    raw = [_coerce_to_item(x) for x in items]
    if not raw:
        return []

    # ---- 阶段 1：精确去重 ----
    fp_groups: dict[str, list[NewsItem]] = {}
    for it in raw:
        fp_groups.setdefault(it.fingerprint(), []).append(it)

    stage1 = [_merge_group(g) for g in fp_groups.values()]

    # ---- 预编码：一次性批量请求，避免在 O(N²) 循环里重复请求 ----
    from valueagents.agents.utils import news_embedding
    semantic_ok = news_embedding.precompute_for_items(stage1)
    if not semantic_ok:
        logger.info("[news_dedup] semantic embedding unavailable; using trigram fallback")

    # ---- 阶段 2：模糊去重（union-find）----
    n = len(stage1)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            if not _dates_close(stage1[i].date, stage1[j].date, date_tolerance_days):
                continue
            sim = title_similarity(stage1[i].title, stage1[j].title)
            if sim >= similarity_threshold:
                union(i, j)

    clusters: dict[int, list[NewsItem]] = {}
    for i, it in enumerate(stage1):
        clusters.setdefault(find(i), []).append(it)

    # ---- 阶段 3：簇内聚度校验（防止链式合并）----
    #
    # 背景：union-find 是 single-linkage，A-B-C-D 只要相邻 pair 都过阈值，
    #       即使 A 和 D 相似度很低，也会被合并成一个大簇。
    # 策略：每个簇选一个 anchor（最可信、summary 最长的），
    #       凡是与 anchor 相似度不足，或与 anchor 日期差太远的成员，踢出单列。
    #
    final_clusters: list[list[NewsItem]] = []
    for cluster_items in clusters.values():
        if len(cluster_items) == 1:
            final_clusters.append(cluster_items)
            continue

        # anchor 选择：source_tier 最小（最可信）；tier 相同选 summary 最长的
        anchor = min(
            cluster_items,
            key=lambda x: (x.source_tier, -len(x.summary or "")),
        )

        keep: list[NewsItem] = [anchor]
        kicked: list[NewsItem] = []
        for it in cluster_items:
            if it is anchor:
                continue
            sim = title_similarity(anchor.title, it.title)
            date_ok = _dates_close(anchor.date, it.date, date_tolerance_days)
            if sim >= similarity_threshold and date_ok:
                keep.append(it)
            else:
                kicked.append(it)

        final_clusters.append(keep)
        # 被踢出的各自成为单条（不再递归合并，避免二次链式）
        for it in kicked:
            final_clusters.append([it])

    return [_merge_group(g) for g in final_clusters]


def rank_news(items: Iterable[NewsItem | dict]) -> list[NewsItem]:
    """
    可信度排序：
      date desc（新在前） → source_tier asc（可信在前） → source_count desc（多源印证在前）
    """
    coerced = [_coerce_to_item(x) for x in items]

    def key(it: NewsItem):
        # date 反序：用负的时间戳
        dt = _parse_date(it.date) or datetime(1970, 1, 1)
        return (-dt.timestamp(), it.source_tier, -it.source_count, it.title)

    return sorted(coerced, key=key)


def dedup_and_rank(
    items: Iterable[NewsItem | dict],
    similarity_threshold: float = 0.75,
    date_tolerance_days: int = 1,
) -> list[NewsItem]:
    """便捷入口：先去重，再排序。"""
    deduped = dedup_news(
        items,
        similarity_threshold=similarity_threshold,
        date_tolerance_days=date_tolerance_days,
    )
    return rank_news(deduped)


def summarize_dedup(
    items_before: Sequence[NewsItem | dict],
    items_after: Sequence[NewsItem],
) -> dict:
    """返回去重前后的统计，用于日志和测试断言。"""
    n_before = len(items_before)
    n_after = len(items_after)
    multi_source = sum(1 for it in items_after if it.source_count > 1)
    return {
        "before": n_before,
        "after": n_after,
        "removed": n_before - n_after,
        "compression_ratio": (1 - n_after / n_before) if n_before else 0.0,
        "multi_source_events": multi_source,
    }
