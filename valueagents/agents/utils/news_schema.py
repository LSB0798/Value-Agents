# valueagents/agents/utils/news_schema.py
"""
统一新闻数据模型与来源分级。

所有新闻源（Finnhub / Alpha Vantage / GNews / Yahoo）在进入聚合器前，
必须先归一化为 NewsItem。这样后续的去重、排序、缓存都只面对一种结构。
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 来源分级（source_tier）
# tier 越小，可信度越高
# ---------------------------------------------------------------------------
SOURCE_TIER: dict[str, int] = {
    # ---- Tier 1: 一手信源 / 官方公告 ----
    "sec": 1,
    "company": 1,
    "businesswire": 1,
    "prnewswire": 1,
    "globenewswire": 1,

    # ---- Tier 2: 一线财经媒体 ----
    "reuters": 2,
    "bloomberg": 2,
    "wsj": 2,
    "wall street journal": 2,
    "financial times": 2,
    "ft": 2,
    "cnbc": 2,
    "barron's": 2,
    "barrons": 2,
    "the economist": 2,

    # ---- Tier 3: 二线财经 / 综合媒体 ----
    "yahoo": 3,
    "yahoo finance": 3,
    "marketwatch": 3,
    "seekingalpha": 3,
    "seeking alpha": 3,
    "investing.com": 3,
    "benzinga": 3,
    "the motley fool": 3,
    "motley fool": 3,
    "zacks": 3,
    "barrons.com": 3,
    "thestreet": 3,
    "investopedia": 3,
    "forbes": 3,
    "fortune": 3,
    "chartmill": 3,
    "the globe and mail": 3,

    # ---- Tier 4: 聚合器 / 低信噪比 ----
    "moomoo": 4,
    "finnhub": 4,
    "gnews": 4,
    "alpha_vantage": 4,
    "alphavantage": 4,
    "stocktwits": 4,
    "reddit": 4,
    "twitter": 4,
    "x": 4,
}

DEFAULT_TIER = 3  # 未知来源默认按二线财经媒体对待

# ---------------------------------------------------------------------------
# 日期修复
# ---------------------------------------------------------------------------
_DATE_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def repair_date(raw: str) -> str:
    """
    尝试把各种畸形日期修复成 YYYY-MM-DD。失败返回空字符串。

    支持：
      - "2026-09-19"           → 原样
      - "2026-09-19T12:00:00"  → 2026-09-19
      - "20260921T2"           → 2026-09-21   （Alpha Vantage 被截断）
      - "20260921T120000"      → 2026-09-21
      - "20260921"             → 2026-09-21
      - "2026/09/19"           → 2026-09-19
      - 其他 → ""
    """
    if not raw or not isinstance(raw, str):
        return ""
    s = raw.strip()

    # 1) 已是 ISO 格式
    if _DATE_ISO_RE.match(s):
        try:
            datetime.strptime(s[:10], "%Y-%m-%d")
            return s[:10]
        except ValueError:
            return ""

    # 2) YYYYMMDD 开头（后面可能跟 T... 垃圾）
    if len(s) >= 8 and s[:8].isdigit():
        y, m, d = s[:4], s[4:6], s[6:8]
        try:
            datetime.strptime(f"{y}-{m}-{d}", "%Y-%m-%d")
            return f"{y}-{m}-{d}"
        except ValueError:
            return ""

    # 3) YYYY/MM/DD
    if len(s) >= 10 and s[4] == "/" and s[7] == "/":
        y, m, d = s[:4], s[5:7], s[8:10]
        try:
            datetime.strptime(f"{y}-{m}-{d}", "%Y-%m-%d")
            return f"{y}-{m}-{d}"
        except ValueError:
            return ""

    return ""


# ---------------------------------------------------------------------------
# 情绪标签归一化
# ---------------------------------------------------------------------------
_SENTIMENT_MAP = {
    "bullish": "bullish",
    "somewhat-bullish": "bullish",
    "somewhat bullish": "bullish",
    "bearish": "bearish",
    "somewhat-bearish": "bearish",
    "somewhat bearish": "bearish",
    "neutral": "neutral",
}


def normalize_sentiment(raw) -> str:
    if raw is None:
        return "unknown"
    if isinstance(raw, str):
        return _SENTIMENT_MAP.get(raw.strip().lower(), "unknown")
    return "unknown"

# 归一化 source 名称（小写、去空格、去后缀）
_SOURCE_CLEAN_RE = re.compile(r"[^a-z0-9\.\s]+")


def normalize_source(source: Optional[str]) -> str:
    if not source:
        return "unknown"
    s = source.strip().lower()
    s = _SOURCE_CLEAN_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    # 去掉常见后缀
    for suffix in (".com", " inc", " corp", " ltd"):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
    return s or "unknown"


def get_source_tier(source: Optional[str]) -> int:
    """返回来源可信度等级（1=最高，4=最低）。"""
    key = normalize_source(source)
    if key in SOURCE_TIER:
        return SOURCE_TIER[key]
    # 模糊匹配：source 中包含已知 key
    for known, tier in SOURCE_TIER.items():
        if known in key:
            return tier
    return DEFAULT_TIER


# ---------------------------------------------------------------------------
# 统一新闻条目
# ---------------------------------------------------------------------------
SentimentLabel = Literal["bullish", "bearish", "neutral", "unknown"]


class NewsItem(BaseModel):
    """归一化后的新闻条目。所有新闻源都必须转换为这个结构。"""

    ticker: str
    date: str = Field(description="YYYY-MM-DD")
    title: str
    summary: str = ""
    url: str = ""
    source: str = "unknown"
    source_tier: int = DEFAULT_TIER
    sentiment: SentimentLabel = "unknown"
    provider: str = Field(
        default="unknown",
        description="原始数据供应商：finnhub / alpha_vantage / gnews / yahoo",
    )
    fetched_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds")
    )

    # ---- 去重后由 news_dedup 填充的字段 ----
    corroborating_sources: list[str] = Field(
        default_factory=list,
        description="同一事件的其他报道来源（去重后合并）",
    )
    source_count: int = Field(
        default=1,
        description="该事件被多少家来源报道（含主来源）",
    )

    # 用于去重的规范化指纹（不参与序列化输出，作为方法计算）
    def fingerprint(self) -> str:
        """基于标题的规范化指纹，用于快速精确去重。"""
        norm = self._normalize_title(self.title)
        return hashlib.md5(norm.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_title(title: str) -> str:
        t = (title or "").lower()
        t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def to_dict(self) -> dict:
        d = self.model_dump()
        d["fingerprint"] = self.fingerprint()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "NewsItem":
        # 1) 只保留已知字段
        d = {k: v for k, v in d.items() if k in cls.model_fields}

        # 2) 修复 date
        raw_date = d.get("date") or ""
        fixed_date = repair_date(raw_date)
        if not fixed_date:
            raise ValueError(f"Unrecoverable date: {raw_date!r}")
        d["date"] = fixed_date

        # 3) 补全 / 归一化字段
        if "source_tier" not in d or not isinstance(d.get("source_tier"), int):
            d["source_tier"] = get_source_tier(d.get("source"))
        d["sentiment"] = normalize_sentiment(d.get("sentiment"))
        d.setdefault("provider", "unknown")
        d.setdefault("summary", "")
        d.setdefault("url", "")
        d.setdefault("source", "unknown")

        return cls(**d)


# ---------------------------------------------------------------------------
# 便捷构造函数：从各家 API 的原始输出转成 NewsItem
# ---------------------------------------------------------------------------
def from_finnhub(raw: dict, ticker: str) -> NewsItem:
    ts = raw.get("datetime")
    date = (
        datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        if isinstance(ts, (int, float))
        else (raw.get("date") or "")
    )
    source = raw.get("source") or "finnhub"
    return NewsItem(
        ticker=ticker,
        date=date,
        title=raw.get("headline") or raw.get("title") or "",
        summary=raw.get("summary") or "",
        url=raw.get("url") or "",
        source=source,
        source_tier=get_source_tier(source),
        sentiment="unknown",
        provider="finnhub",
    )


def from_alpha_vantage(raw: dict, ticker: str) -> NewsItem:
    tp = raw.get("time_published") or ""
    date = f"{tp[:4]}-{tp[4:6]}-{tp[6:8]}" if len(tp) >= 8 else ""
    source = raw.get("source") or "alpha_vantage"
    label = (raw.get("overall_sentiment_label") or "").lower()
    sentiment: SentimentLabel = "unknown"
    if "bull" in label:
        sentiment = "bullish"
    elif "bear" in label:
        sentiment = "bearish"
    elif label:
        sentiment = "neutral"
    return NewsItem(
        ticker=ticker,
        date=date,
        title=raw.get("title") or "",
        summary=raw.get("summary") or "",
        url=raw.get("url") or "",
        source=source,
        source_tier=get_source_tier(source),
        sentiment=sentiment,
        provider="alpha_vantage",
    )


def from_gnews(raw: dict, ticker: str) -> NewsItem:
    published = raw.get("publishedAt") or ""
    date = published[:10] if len(published) >= 10 else ""
    source = (raw.get("source") or {}).get("name") or "gnews"
    return NewsItem(
        ticker=ticker,
        date=date,
        title=raw.get("title") or "",
        summary=raw.get("description") or "",
        url=raw.get("url") or "",
        source=source,
        source_tier=get_source_tier(source),
        sentiment="unknown",
        provider="gnews",
    )
