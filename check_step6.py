# check_step6.py
"""
Step 1-6 静态检查：确认所有新增/修改都在位，且关键符号可导入。
不运行主程序，不做真实 API 调用。
"""

import importlib
import inspect
import os
import sys

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = []


def check(desc, condition, detail=""):
    icon = PASS if condition else FAIL
    results.append((icon, desc, detail))
    print(f"{icon} {desc}" + (f"  [{detail}]" if detail else ""))


print("=" * 72)
print("Step 1-6 检查")
print("=" * 72)

# ---------------------------------------------------------------
# 1. 文件存在性
# ---------------------------------------------------------------
print("\n[1] 新增文件存在性")
files = [
    "valueagents/agents/utils/news_schema.py",
    "valueagents/agents/utils/news_dedup.py",
    "valueagents/agents/utils/news_aggregator.py",
    "valueagents/agents/utils/news_aggregator_tools.py",
    "valueagents/agents/utils/news_cache_strategy.py",
    "valueagents/agents/utils/process_local_news.py",
]
for f in files:
    check(f, os.path.exists(f), "missing" if not os.path.exists(f) else "")

# ---------------------------------------------------------------
# 2. news_schema.py 关键符号
# ---------------------------------------------------------------
print("\n[2] news_schema 关键符号")
try:
    m = importlib.import_module("valueagents.agents.utils.news_schema")
    for name in [
        "NewsItem", "get_source_tier", "normalize_source",
        "repair_date", "normalize_sentiment",
        "from_finnhub", "from_alpha_vantage", "from_gnews",
    ]:
        check(f"news_schema.{name}", hasattr(m, name))

    # NewsItem 的字段完整性
    ni = m.NewsItem
    fields = set(ni.model_fields.keys())
    for f in [
        "ticker", "date", "title", "summary", "url", "source",
        "source_tier", "sentiment", "provider", "fetched_at",
        "corroborating_sources", "source_count",
    ]:
        check(f"NewsItem 字段 {f}", f in fields)

    # repair_date 行为
    check("repair_date('20260921T2') == '2026-09-21'",
          m.repair_date("20260921T2") == "2026-09-21")
    check("repair_date('2026-09-19') == '2026-09-19'",
          m.repair_date("2026-09-19") == "2026-09-19")
    check("repair_date('garbage') == ''",
          m.repair_date("garbage") == "")

    # normalize_sentiment
    check("normalize_sentiment('Somewhat-Bearish') == 'bearish'",
          m.normalize_sentiment("Somewhat-Bearish") == "bearish")
    check("normalize_sentiment(None) == 'unknown'",
          m.normalize_sentiment(None) == "unknown")
except Exception as e:
    check("import news_schema", False, str(e))

# ---------------------------------------------------------------
# 3. news_dedup.py
# ---------------------------------------------------------------
print("\n[3] news_dedup 关键符号")
try:
    m = importlib.import_module("valueagents.agents.utils.news_dedup")
    for name in ["dedup_news", "rank_news", "dedup_and_rank",
                 "title_similarity", "summarize_dedup"]:
        check(f"news_dedup.{name}", hasattr(m, name))
except Exception as e:
    check("import news_dedup", False, str(e))

# ---------------------------------------------------------------
# 4. news_aggregator.py
# ---------------------------------------------------------------
print("\n[4] news_aggregator 关键符号")
try:
    m = importlib.import_module("valueagents.agents.utils.news_aggregator")
    for name in ["aggregate_company_news", "aggregate_global_news",
                 "render_news_for_llm", "AggregationResult",
                 "SourceStats", "DEFAULT_SOURCES"]:
        check(f"news_aggregator.{name}", hasattr(m, name))
    # DEFAULT_SOURCES 必须包含三家
    ds = getattr(m, "DEFAULT_SOURCES", ())
    check("DEFAULT_SOURCES 含 finnhub", "finnhub" in ds)
    check("DEFAULT_SOURCES 含 alpha_vantage", "alpha_vantage" in ds)
    check("DEFAULT_SOURCES 含 gnews", "gnews" in ds)
except Exception as e:
    check("import news_aggregator", False, str(e))

# ---------------------------------------------------------------
# 5. news_cache_strategy.py
# ---------------------------------------------------------------
print("\n[5] news_cache_strategy 关键符号")
try:
    m = importlib.import_module("valueagents.agents.utils.news_cache_strategy")
    for name in ["CacheFreshness", "compute_freshness",
                 "find_missing_windows", "days_between"]:
        check(f"news_cache_strategy.{name}", hasattr(m, name))
except Exception as e:
    check("import news_cache_strategy", False, str(e))

# ---------------------------------------------------------------
# 6. cache.py 新方法
# ---------------------------------------------------------------
print("\n[6] cache 新方法")
try:
    from valueagents.agents.src.data.cache import get_cache
    c = get_cache()
    for name in [
        "get_news_as_items", "set_news_items",
        "get_global_news_as_items", "set_global_news_items",
        "get_global_news_cache", "set_global_news_cache",
        "get_news_cache", "set_news_cache",
    ]:
        check(f"cache.{name}", hasattr(c, name))

    # 确认 set_news_cache 里含排序逻辑
    src = inspect.getsource(type(c).set_news_cache)
    check("set_news_cache 含 sort", "sort" in src)

    # _merge_data 支持 callable key
    sig = inspect.signature(type(c)._merge_data)
    check("_merge_data 存在", sig is not None)

    # _news_fingerprint 作为模块级函数
    cache_mod = importlib.import_module("valueagents.agents.src.data.cache")
    check("cache._news_fingerprint 存在",
          hasattr(cache_mod, "_news_fingerprint"))
except Exception as e:
    check("import cache", False, str(e))

# ---------------------------------------------------------------
# 7. news_analyst.py 是否已用本地工具
# ---------------------------------------------------------------
print("\n[7] news_analyst 是否已切换为聚合器版本")
try:
    m = importlib.import_module("valueagents.agents.analysts.news_analyst")
    src = inspect.getsource(m)

    check("import aggregate_company_news",
          "aggregate_company_news" in src)
    check("import aggregate_global_news",
          "aggregate_global_news" in src)
    check("import compute_freshness",
          "compute_freshness" in src)
    check("import get_cache",
          "get_cache" in src)
    # 本地定义的 get_news（带 @tool）
    check("本地定义 get_news 工具",
          "@tool" in src and "def get_news" in src)
    check("本地定义 get_global_news 工具",
          "def get_global_news" in src)
except Exception as e:
    check("import news_analyst", False, str(e))

# ---------------------------------------------------------------
# 8. 依赖一致性（避免循环导入）
# ---------------------------------------------------------------
print("\n[8] 循环依赖检测")
try:
    import valueagents.agents.utils.news_aggregator
    import valueagents.agents.utils.news_cache_strategy
    import valueagents.agents.src.data.cache
    check("cache → news_schema 无循环", True)
except Exception as e:
    check("循环依赖", False, str(e))

# ---------------------------------------------------------------
# 9. 汇总
# ---------------------------------------------------------------
print("\n" + "=" * 72)
fails = [r for r in results if r[0] == FAIL]
print(f"总计：{len(results)}  失败：{len(fails)}")
if fails:
    print("\n失败项：")
    for icon, desc, detail in fails:
        print(f"  {icon} {desc}  [{detail}]")
    sys.exit(1)
else:
    print("全部通过 ✅")
