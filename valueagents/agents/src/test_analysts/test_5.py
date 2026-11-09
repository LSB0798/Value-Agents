#!/usr/bin/env python
"""
ROIC.ai 季度数据探查（修正版）
- 修正字段名：is_sales_revenue_turnover / is_net_income
- 修正现金流端点：/v2/fundamental/cash-flow/{identifier}
- 验证 AAPL Q4 单季值是否直接返回
"""
import requests
import os
import json

API_KEY = os.environ.get("ROIC_API_KEY", "w0W0fpmdjfiKw92Xd9J2jpY2yyqJtsbn")
BASE = "https://api.roic.ai/v2/fundamental"


def _get(endpoint: str, params: dict) -> dict | None:
    url = f"{BASE}/{endpoint}"
    params["apikey"] = API_KEY
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"🔗 {resp.url}")
        print(f"   HTTP {resp.status_code}")
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"   ❌ {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        return None


def probe_aapl():
    print("=" * 100)
    print("ROIC.ai API 探查（修正版）— AAPL")
    print("=" * 100)

    # ---------- 1) 收入表（季度）----------
    print("\n[1] Income Statement (quarterly) — 修正字段名")
    print("-" * 100)
    data = _get("income-statement/AAPL", {
        "period": "quarterly",
        "limit": 8,
        "order": "DESC",
    })
    if data:
        print(f"   ✅ 返回 {len(data)} 条记录")
        print(f"   字段示例: {list(data[0].keys())[:15]}")
        print(f"\n   {'fiscal_year':<12} {'period':<10} {'revenue':>18} {'net_income':>18}")
        print(f"   {'-'*60}")
        for row in data:
            fy = row.get("fiscal_year", "")
            period = row.get("period", "")
            rev = row.get("is_sales_revenue_turnover")
            ni = row.get("is_net_income")
            rev_str = f"{rev:>18,.0f}" if isinstance(rev, (int, float)) else f"{str(rev):>18}"
            ni_str = f"{ni:>18,.0f}" if isinstance(ni, (int, float)) else f"{str(ni):>18}"
            print(f"   {str(fy):<12} {str(period):<10} {rev_str} {ni_str}")

    # ---------- 2) 资产负债表（季度）----------
    print("\n[2] Balance Sheet (quarterly) — 修正字段名")
    print("-" * 100)
    data = _get("balance-sheet/AAPL", {
        "period": "quarterly",
        "limit": 8,
        "order": "DESC",
    })
    if data:
        print(f"   ✅ 返回 {len(data)} 条记录")
        print(f"   权益字段: bs_total_equity, 资产字段: bs_tot_asset")
        print(f"\n   {'fiscal_year':<12} {'period':<10} {'total_assets':>18} {'total_equity':>18}")
        print(f"   {'-'*60}")
        for row in data:
            fy = row.get("fiscal_year", "")
            period = row.get("period", "")
            ta = row.get("bs_tot_asset")
            eq = row.get("bs_total_equity")
            ta_str = f"{ta:>18,.0f}" if isinstance(ta, (int, float)) else f"{str(ta):>18}"
            eq_str = f"{eq:>18,.0f}" if isinstance(eq, (int, float)) else f"{str(eq):>18}"
            print(f"   {str(fy):<12} {str(period):<10} {ta_str} {eq_str}")

    # ---------- 3) 现金流量表（季度）— 修正端点 ----------
    print("\n[3] Cash Flow Statement (quarterly) — 修正端点 /cash-flow/")
    print("-" * 100)
    data = _get("cash-flow/AAPL", {
        "period": "quarterly",
        "limit": 8,
        "order": "DESC",
    })
    if data:
        print(f"   ✅ 返回 {len(data)} 条记录")
        # 找到现金流的关键字段
        cf_keys = [k for k in data[0].keys() if 'cash' in k.lower() or 'fcf' in k.lower() or 'capex' in k.lower() or 'free' in k.lower()]
        print(f"   现金流字段: {cf_keys[:10]}")
        # 尝试常见的自由现金流字段名
        fcf_field = None
        for candidate in ["cf_free_cash_flow", "free_cash_flow", "fcf", "cf_fcf"]:
            if candidate in data[0]:
                fcf_field = candidate
                break
        if fcf_field:
            print(f"\n   {'fiscal_year':<12} {'period':<10} {fcf_field:>18}")
            print(f"   {'-'*50}")
            for row in data:
                fy = row.get("fiscal_year", "")
                period = row.get("period", "")
                fcf = row.get(fcf_field)
                fcf_str = f"{fcf:>18,.0f}" if isinstance(fcf, (int, float)) else f"{str(fcf):>18}"
                print(f"   {str(fy):<12} {str(period):<10} {fcf_str}")

    # ---------- 4) 盈利能力比率（季度）----------
    print("\n[4] Profitability Ratios (quarterly)")
    print("-" * 100)
    data = _get("ratios/profitability/AAPL", {
        "period": "quarterly",
        "limit": 8,
        "order": "DESC",
    })
    if data:
        print(f"   ✅ 返回 {len(data)} 条记录")
        print(f"\n   {'fiscal_year':<12} {'period':<10} {'ROIC':>10} {'ROE':>10} {'gross_margin':>14}")
        print(f"   {'-'*60}")
        for row in data:
            fy = row.get("fiscal_year", "")
            period = row.get("period", "")
            roic = row.get("return_on_inv_capital")
            roe = row.get("return_com_eqy")
            gm = row.get("gross_margin")
            roic_str = f"{roic:>10.2f}" if isinstance(roic, (int, float)) else f"{str(roic):>10}"
            roe_str = f"{roe:>10.2f}" if isinstance(roe, (int, float)) else f"{str(roe):>10}"
            gm_str = f"{gm:>14.2f}" if isinstance(gm, (int, float)) else f"{str(gm):>14}"
            print(f"   {str(fy):<12} {str(period):<10} {roic_str} {roe_str} {gm_str}")


if __name__ == "__main__":
    probe_aapl()