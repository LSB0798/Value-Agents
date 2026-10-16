# test_sentiment_skill.py
import os
import json
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 设置财务数据 API Key（必须，用于获取财务数据，但 sentiment 其实不需要财务数据，所以可省略）
# 但为了兼容，保留
if not os.getenv("FINANCIAL_DATASETS_API_KEY"):
    # 你可以选择在这里显式设置，或从 .env 加载
    # 但 sentiment 不依赖财务数据，所以即使不设置也能运行
    print("ℹ️  FINANCIAL_DATASETS_API_KEY not set. 如果只运行 sentiment，不影响。")

from valueagents.agents.skills.sentiment_skill.skill import execute
from valueagents.agents.skills.loader import load_skill

def test_direct_execute():
    print("\n=== Test 1: Direct execute() call ===")
    result = execute(ticker="AAPL", end_date="2026-06-30")
    data = json.loads(result)
    print(f"Ticker: {data['ticker']}")
    print(f"Signal: {data['signal']}")
    print(f"Confidence: {data['confidence']}")
    # 打印部分 reasoning
    reasoning = data.get('reasoning', {})
    print(f"Insider signal: {reasoning.get('insider_trading', {}).get('signal', 'N/A')}")
    print(f"News signal: {reasoning.get('news_sentiment', {}).get('signal', 'N/A')}")
    print("✅ Direct execute test passed.\n")

def test_loader():
    print("\n=== Test 2: Load via loader.py ===")
    skill_dir = Path(__file__).parent / "sentiment_skill"
    tool = load_skill(skill_dir)
    if tool is None:
        print("❌ Failed to load skill")
        return
    print(f"Loaded tool: {tool.name}")
    result = tool.invoke({"ticker": "AAPL", "end_date": "2026-06-30"})
    data = json.loads(result)
    print(f"Result: {data['signal']} (conf: {data['confidence']})")
    print("✅ Loader test passed.\n")

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Sentiment Skill")
    print("=" * 50)
    try:
        test_direct_execute()
        test_loader()
        print("🎉 All tests passed!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
