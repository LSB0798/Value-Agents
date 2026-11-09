#!/usr/bin/env python
"""
测试 FinancialMetrics 模型包含的字段，确认 enterprise_value 是否存在
"""

import os
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"

import sys
from valueagents.agents.src.tools.api import get_financial_metrics
from valueagents.agents.src.data.models import FinancialMetrics

def test_fields():
    print("🔍 检查 FinancialMetrics 模型字段:")
    fields = list(FinancialMetrics.model_fields.keys())
    for f in fields:
        print(f"  - {f}")
    print(f"\n总字段数: {len(fields)}")
    
    # 检查 enterprise_value 是否存在
    if "enterprise_value" in fields:
        print("\n✅ enterprise_value 存在于模型中")
    else:
        print("\n❌ enterprise_value 不在模型中")
        print("建议: 在 agent 内部直接计算 EV/EBIT 或修改模型添加该字段")

    # 获取真实数据测试
    print("\n🔍 获取 AAPL 的 FinancialMetrics 实例:")
    metrics = get_financial_metrics("AAPL", "2026-07-10", period="ttm", limit=1)
    if metrics:
        m = metrics[0]
        print(f"  字段值 (非 None):")
        for field, value in m.model_dump().items():
            if value is not None:
                print(f"    {field}: {value}")
    else:
        print("  未获取到数据")

if __name__ == "__main__":
    test_fields()
