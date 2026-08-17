# test_valuation_skill.py
import os
import json
import sys
from pathlib import Path

import os
# 设置 API Key（临时测试用）
os.environ["FINANCIAL_DATASETS_API_KEY"] = "7822668c-eb7d-43b6-bee4-fb31a46e182a"
# 将项目根目录加入 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 检查环境变量
if not os.getenv("FINANCIAL_DATASETS_API_KEY"):
    print("⚠️  Warning: FINANCIAL_DATASETS_API_KEY not set. 请设置后再运行。")

from valueagents.agents.skills.valuation_skill.skill import execute
from valueagents.agents.skills.loader import load_skill


def test_direct_execute():
    print("\n=== Test 1: Direct execute() call ===")
    result = execute(ticker="AAPL", end_date="2026-06-30")
    data = json.loads(result)
    print(f"Ticker: {data['ticker']}")
    print(f"Signal: {data['signal']}")
    print(f"Confidence: {data['confidence']}")
    
    # 处理 reasoning（可能是 dict 或 str）
    reasoning = data['reasoning']
    if isinstance(reasoning, dict):
        reasoning_str = json.dumps(reasoning, indent=2)[:300]
    else:
        reasoning_str = str(reasoning)[:300]
    print(f"Reasoning (truncated): {reasoning_str}...")
    print("✅ Direct execute test passed.\n")


def test_loader():
    print("\n=== Test 2: Load via loader.py ===")
    skill_dir = Path(__file__).parent / "valuation_skill"
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
    print("Testing Valuation Skill")
    print("=" * 50)
    
    try:
        test_direct_execute()
        test_loader()
        print("🎉 All tests passed!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
