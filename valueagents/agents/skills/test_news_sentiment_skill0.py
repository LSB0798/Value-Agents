# test_news_sentiment_skill.py
import os
import json
import sys
from pathlib import Path

# ===== 设置 Alpha Vantage API Key（与 api.py 默认一致）=====
os.environ["ALPHA_VANTAGE_API_KEY"] = "LEPNUFM9ZGGRXWDR"

# 将项目根目录加入 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 检查环境变量（可选）
print(f"🔑 ALPHA_VANTAGE_API_KEY = {os.environ.get('ALPHA_VANTAGE_API_KEY', 'Not set')}")

from valueagents.agents.skills.news_sentiment_skill.skill import execute
from valueagents.agents.skills.loader import load_skill

# 添加调试：直接测试 get_news 工具
def debug_get_news():
    print("\n--- Debug: Direct get_news call ---")
    try:
        from valueagents.agents.utils.agent_utils import get_news
        result = get_news.invoke({
            "ticker": "AAPL",
            "start_date": "2026-06-23",
            "end_date": "2026-06-30"
        })
        print(f"📰 get_news returned {len(result)} characters")
        print(f"Preview: {result[:300]}...")
        if "No news found" in result or "Error" in result:
            print("⚠️  API call returned no articles or error.")
        else:
            print("✅ API call appears successful.")
    except Exception as e:
        print(f"❌ Error calling get_news: {e}")


def test_direct_execute():
    print("\n=== Test 1: Direct execute() call ===")
    result = execute(ticker="AAPL", end_date="2026-06-30")
    data = json.loads(result)
    print(f"Ticker: {data['ticker']}")
    print(f"Signal: {data['signal']}")
    print(f"Confidence: {data['confidence']}")
    if isinstance(data['reasoning'], dict):
        print("Reasoning (keys):", list(data['reasoning'].keys()))
        for key, value in data['reasoning'].items():
            if isinstance(value, dict):
                print(f"  {key}: signal={value.get('signal', 'N/A')}, conf={value.get('confidence', 'N/A')}")
                metrics = value.get('metrics', {})
                print(f"      articles: {metrics.get('total_articles', 0)} (bullish={metrics.get('bullish_articles', 0)}, bearish={metrics.get('bearish_articles', 0)}, neutral={metrics.get('neutral_articles', 0)})")
            else:
                print(f"  {key}: {str(value)[:60]}...")
    else:
        print(f"Reasoning: {data['reasoning'][:200]}...")
    print("✅ Direct execute test passed.\n")


def test_loader():
    print("\n=== Test 2: Load via loader.py ===")
    skill_dir = Path(__file__).parent / "news_sentiment_skill"
    tool = load_skill(skill_dir)
    
    if tool is None:
        print("❌ Failed to load skill")
        return
    
    print(f"Loaded tool: {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Args schema: {tool.args_schema}")
    
    result = tool.invoke({"ticker": "AAPL", "end_date": "2026-06-30"})
    data = json.loads(result)
    print(f"Result: {data['signal']} (conf: {data['confidence']})")
    print("✅ Loader test passed.\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Testing News Sentiment Skill")
    print("=" * 50)
    
    try:
        debug_get_news()          # 先调试原始工具
        test_direct_execute()
        test_loader()
        print("🎉 All tests passed!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
