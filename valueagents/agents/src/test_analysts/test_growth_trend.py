#!/usr/bin/env python
import os
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"

import sys
import pandas as pd
from valueagents.agents.src.tools.api import get_financial_metrics
from valueagents.agents.src.analysts.growth_agent import _calculate_trend

ticker = "AAPL"
end_date = "2026-07-10"
limit = 12

print(f"获取 {ticker} 的财务指标 (EDGAR 模式, limit={limit})...")
metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=limit)
print(f"共获取 {len(metrics)} 条记录\n")

if metrics:
    # 提取增长率序列（注意字段名）
    rev_growth = [m.revenue_growth for m in metrics if hasattr(m, 'revenue_growth')]
    eps_growth = [m.earnings_growth for m in metrics if hasattr(m, 'earnings_growth')]
    fcf_growth = [m.free_cash_flow_growth for m in metrics if hasattr(m, 'free_cash_flow_growth')]

    print(f"Revenue growth sequence (length {len(rev_growth)}): {rev_growth}")
    print(f"EPS growth sequence (length {len(eps_growth)}): {eps_growth}")
    print(f"FCF growth sequence (length {len(fcf_growth)}): {fcf_growth}\n")

    # 手动计算趋势
    rev_trend = _calculate_trend(rev_growth) if rev_growth else None
    eps_trend = _calculate_trend(eps_growth) if eps_growth else None
    fcf_trend = _calculate_trend(fcf_growth) if fcf_growth else None

    print(f"Revenue trend: {rev_trend}")
    print(f"EPS trend: {eps_trend}")
    print(f"FCF trend: {fcf_trend}")
else:
    print("没有获取到数据")
