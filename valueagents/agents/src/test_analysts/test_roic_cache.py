import os
import sys
import json
sys.path.insert(0, '/data/lishuaibing/valueagents/ValueAgents')  # 根据实际路径调整

from valueagents.agents.src.tools.api import _fetch_roic_quarters
from valueagents.default_config import DEFAULT_CONFIG

def test_roic_cache():
    ticker = "AAPL"
    limit = 8  # 获取 8 个季度
    print(f"🔍 正在获取 {ticker} 的 {limit} 个季度数据...")
    
    # 调用数据提取函数（内部会自动存储）
    data = _fetch_roic_quarters(ticker, limit)
    print(f"✅ 数据获取完成:")
    print(f"   - 利润表: {len(data['income'])} 条")
    print(f"   - 资产负债表: {len(data['balance'])} 条")
    print(f"   - 现金流量表: {len(data['cashflow'])} 条")
    print(f"   - 比率: {len(data['ratios'])} 条")
    
    # 检查磁盘缓存文件
    cache_dir = os.path.join(DEFAULT_CONFIG["data_cache_dir"], "fundamentals", "quarterly")
    file_path = os.path.join(cache_dir, f"{ticker}_quarters.json")
    
    if os.path.exists(file_path):
        print(f"✅ 缓存文件已创建: {file_path}")
        with open(file_path, 'r') as f:
            saved_data = json.load(f)
            print(f"   - 文件中的利润表条目数: {len(saved_data.get('income', []))}")
            if saved_data.get('income'):
                print(f"   - 示例第一条数据: {saved_data['income'][0]}")
    else:
        print(f"❌ 缓存文件未找到: {file_path}")

if __name__ == "__main__":
    test_roic_cache()
