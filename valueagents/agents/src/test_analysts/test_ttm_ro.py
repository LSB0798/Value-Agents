#!/usr/bin/env python
import os
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"

import sys
import pandas as pd
from valueagents.agents.src.tools.api import _get_financial_metrics_edgar_ttm

ticker = "AAPL"
end_date = "2026-07-10"
limit = 5

metrics = _get_financial_metrics_edgar_ttm(ticker, end_date, limit)
if metrics:
    for m in metrics:
        print(f"Report period: {m.report_period}")
        print(f"  revenue: {m.revenue}")
        print(f"  net_income: {m.net_income}")
        print(f"  shareholders_equity: {m.shareholders_equity}")
        print(f"  return_on_equity: {m.return_on_equity}")
        print("---")
else:
    print("No metrics returned.")
