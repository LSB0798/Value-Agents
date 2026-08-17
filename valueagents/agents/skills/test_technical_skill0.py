# test_technical_skill.py
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

# 检查环境变量（可选）
if not os.getenv("FINANCIAL_DATASETS_API_KEY"):
    print("⚠️  Warning: FINANCIAL_DATASETS_API_KEY not set. 价格数据可能仅使用 yfinance，无需此 Key。")

from valueagents.agents.skills.technical_skill.skill import execute
from valueagents.agents.skills.loader import load_skill


def test_direct_execute():
    print("\n=== Test 1: Direct execute() call ===")
    # 注意：技术分析需要 start_date 和 end_date
    start_date = "2025-12-01"
    end_date = "2026-06-30"
    result = execute(ticker="AAPL", start_date=start_date, end_date=end_date)
    data = json.loads(result)
    print(f"Ticker: {data['ticker']}")
    print(f"Signal: {data['signal']}")
    print(f"Confidence: {data['confidence']}")
    # 打印前200字符的reasoning
    reasoning_preview = data.get('reasoning', '')
    if isinstance(reasoning_preview, dict):
        reasoning_preview = json.dumps(reasoning_preview, indent=2)[:200]
    else:
        reasoning_preview = str(reasoning_preview)[:200]
    print(f"Reasoning: {reasoning_preview}...")
    print("✅ Direct execute test passed.\n")


def test_loader():
    print("\n=== Test 2: Load via loader.py ===")
    skill_dir = Path(__file__).parent / "technical_skill"
    tool = load_skill(skill_dir)
    
    if tool is None:
        print("❌ Failed to load skill")
        return
    
    print(f"Loaded tool: {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Args schema: {tool.args_schema}")
    
    result = tool.invoke({
        "ticker": "AAPL",
        "start_date": "2025-12-01",
        "end_date": "2026-06-30"
    })
    data = json.loads(result)
    print(f"Result: {data['signal']} (conf: {data['confidence']})")
    print("✅ Loader test passed.\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Technical Skill")
    print("=" * 50)
    
    try:
        test_direct_execute()
        test_loader()
        print("🎉 All tests passed!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
