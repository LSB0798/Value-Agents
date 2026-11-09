# test_news_cache.py
import os
import sys
import json
import datetime
sys.path.insert(0, '/data/lishuaibing/valueagents/ValueAgents')

# 设置环境变量，确保新闻数据源可用（Alpha Vantage 或 Finnhub）
# 请确保您的 .env 文件或环境中有对应的 API Key
os.environ.setdefault("ALPHA_VANTAGE_API_KEY", "LEPNUFM9ZGGRXWDR")
os.environ.setdefault("FINNHUB_API_KEY", "d8tr0gpr01qhcnk5oj3gd8tr0gpr01qhcnk5oj40")

from valueagents.agents.src.tools.api import get_company_news
from valueagents.agents.src.data.cache import get_cache
from valueagents.default_config import DEFAULT_CONFIG

def test_news_cache():
    ticker = "AAPL"
    end_date = "2026-07-29"
    start_date = "2026-07-22"
    limit = 10

    print("=== 测试1: 首次调用（应从 API 获取并缓存） ===")
    news1 = get_company_news(ticker, end_date, start_date, limit)
    print(f"获取到 {len(news1)} 条新闻")
    if news1:
        print("首条新闻:", news1[0].title, news1[0].date, news1[0].source)

    # 检查缓存文件
    cache = get_cache()
    cached = cache.get_news_cache(ticker)
    print(f"缓存中存储了 {len(cached)} 条总记录（{ticker}）")

    print("\n=== 测试2: 第二次调用（应从缓存读取） ===")
    news2 = get_company_news(ticker, end_date, start_date, limit)
    print(f"获取到 {len(news2)} 条新闻")
    if news2:
        print("首条新闻:", news2[0].title, news2[0].date, news2[0].source)

    # 验证数量一致
    assert len(news1) == len(news2), "新闻数量不一致，缓存可能未生效"
    print("✅ 缓存测试通过：两次返回相同数量的新闻。")

    print("\n=== 测试3: 不同日期范围（应从缓存过滤） ===")
    news3 = get_company_news(ticker, end_date, None, 5)  # 无开始日期，取最新5条
    print(f"获取到 {len(news3)} 条新闻（最新5条）")
    for i, n in enumerate(news3[:3]):
        print(f"{i+1}. {n.date} - {n.title[:60]}...")

    print("\n=== 测试4: 验证缓存文件 ===")
    cache_dir = os.path.join(DEFAULT_CONFIG["data_cache_dir"], "news")
    file_path = os.path.join(cache_dir, f"{ticker}_news.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
        print(f"缓存文件存在，包含 {len(data)} 条记录。")
        print("前3条记录日期:", [r.get('date') for r in data[:3]])
    else:
        print("⚠️ 缓存文件不存在（可能因未获取到数据）")

    print("\n=== 测试5: 精确日期过滤 ===")
    news4 = get_company_news(ticker, end_date, "2026-07-29", 10)  # 仅查询 2026-07-29 当天
    print(f"获取到 {len(news4)} 条日期为 2026-07-29 的新闻")
    for n in news4:
        print(f"  {n.date} - {n.title[:60]}...")

    print("\n✅ 所有测试完成。")

if __name__ == "__main__":
    test_news_cache()
