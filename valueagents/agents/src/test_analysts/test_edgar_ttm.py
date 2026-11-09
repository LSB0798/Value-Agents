#!/usr/bin/env python
"""
测试 EDGAR TTM 数据，检查所有 FinancialMetrics 字段的填充情况
"""
import os
import sys
from pprint import pprint

# 强制启用 EDGAR（确保使用免费数据）
os.environ["USE_EDGAR"] = "true"

# 添加项目路径（如果运行位置不在项目根目录）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import get_financial_metrics, FinancialMetrics

def test_ttm_fields():
    ticker = "AAPL"
    end_date = "2025-12-31"
    limit = 3
    print(f"Testing get_financial_metrics for {ticker}, period='ttm', limit={limit}")
    print("=" * 80)

    metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=limit)
    if not metrics:
        print("❌ No metrics returned")
        return

    print(f"✅ Returned {len(metrics)} records\n")

    # 定义需要检查的关键字段（包括之前缺失的）
    fields_to_check = [
        'return_on_invested_capital',
        'operating_income_growth',
        'ebitda_growth',
        'enterprise_value_to_ebitda_ratio',
        'quick_ratio',
        'cash_ratio',
        'asset_turnover',
        'inventory_turnover',
        'working_capital_turnover',
        'debt_to_assets',
        'interest_coverage',
        'payout_ratio',
        'peg_ratio',
        'enterprise_value',
        'enterprise_value_to_revenue_ratio',
        'free_cash_flow_yield',
        'price_to_earnings_ratio',
        'price_to_book_ratio',
        'price_to_sales_ratio'
    ]

    for idx, m in enumerate(metrics):
        print(f"--- Record {idx+1}: report_period = {m.report_period} ---")
        # 打印所有非空字段
        non_null = {k: v for k, v in m.model_dump().items() if v is not None}
        print(f"Non-null fields count: {len(non_null)}")
        # 显示关键字段的值
        print("\nKey fields:")
        for f in fields_to_check:
            value = getattr(m, f, None)
            if value is not None:
                print(f"  ✅ {f}: {value}")
            else:
                print(f"  ❌ {f}: None")
        print("-" * 40)

    # 总结：检查是否有字段在所有记录中都为 None
    all_fields = set(FinancialMetrics.model_fields.keys())
    null_fields = set()
    for m in metrics:
        for field in all_fields:
            if getattr(m, field, None) is None:
                null_fields.add(field)
    print(f"\n📊 在所有记录中始终为 None 的字段 ({len(null_fields)} 个):")
    for f in sorted(null_fields):
        print(f"  - {f}")

if __name__ == "__main__":
    test_ttm_fields()

