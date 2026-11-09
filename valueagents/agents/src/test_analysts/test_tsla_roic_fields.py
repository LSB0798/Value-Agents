#!/usr/bin/env python
"""
测试 TSLA 的 ROIC 数据中 bs_total_equity 和 bs_sh_out 是否存在。
"""

import sys
import os
import json
import requests
import time

# 复制 api.py 中的 _roic_request 函数
def _roic_request(endpoint: str, params: dict, retries=3, delay=12) -> dict | None:
    api_key = os.environ.get("ROIC_API_KEY", "w0W0fpmdjfiKw92Xd9J2jpY2yyqJtsbn")
    if not api_key:
        return None
    url = f"https://api.roic.ai/v2/fundamental/{endpoint}"
    params["apikey"] = api_key
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                time.sleep(delay * (attempt + 1))
                continue
            else:
                return None
        except Exception:
            time.sleep(delay)
            continue
    return None

def test_ticker(ticker="TSLA"):
    print(f"测试 {ticker} 的 ROIC 资产负债表和利润表字段")
    
    # 获取最近季度数据
    balance = _roic_request(f"balance-sheet/{ticker}", {"period": "quarterly", "limit": 5, "order": "DESC"})
    income = _roic_request(f"income-statement/{ticker}", {"period": "quarterly", "limit": 5, "order": "DESC"})
    
    if not balance:
        print("❌ 未获取到资产负债表")
        return
    if not income:
        print("❌ 未获取到利润表")
        return
    
    # 打印最新一条记录的字段
    latest_bal = balance[0]
    latest_inc = income[0]
    
    print("\n最新资产负债表字段（部分）:")
    print(f"  bs_total_equity: {latest_bal.get('bs_total_equity')}")
    print(f"  bs_sh_out: {latest_bal.get('bs_sh_out')}")
    print(f"  bs_tot_asset: {latest_bal.get('bs_tot_asset')}")
    print(f"  bs_tot_liab: {latest_bal.get('bs_tot_liab')}")
    
    print("\n最新利润表字段（部分）:")
    print(f"  is_net_income: {latest_inc.get('is_net_income')}")
    print(f"  is_oper_income: {latest_inc.get('is_oper_income')}")
    
    # 检查是否缺失
    equity = latest_bal.get('bs_total_equity')
    shares = latest_bal.get('bs_sh_out')
    if equity is None or shares is None:
        print("\n⚠️  bs_total_equity 或 bs_sh_out 缺失，导致 book_value_per_share 无法计算。")
    else:
        print("\n✅ 数据完整，可计算 book_value_per_share。")

if __name__ == "__main__":
    test_ticker("TSLA")
