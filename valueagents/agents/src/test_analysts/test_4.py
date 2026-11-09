#!/usr/bin/env python
"""
通用探查：检查任意公司在 SEC XBRL 里能否直接获取 Q4 单季值。
用法：python test_probe.py MSFT
"""
import requests
import sys
from collections import defaultdict

USER_AGENT = "ValueAgents research your_email@example.com"  # ← 改成你自己的邮箱
SEC_CIK_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
REQUEST_INTERVAL = 0.15


def _get_json(url: str) -> dict:
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def ticker_to_cik(ticker: str) -> str:
    data = _get_json(SEC_CIK_MAP_URL)
    for v in data.values():
        if v["ticker"].upper() == ticker.upper():
            return f"{v['cik_str']:010d}"
    raise ValueError(f"Ticker {ticker} not found")


def probe_company(ticker: str):
    cik = ticker_to_cik(ticker)
    print(f"\n{'='*100}")
    print(f"探查公司: {ticker} (CIK: {cik})")
    print(f"{'='*100}")

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    facts = _get_json(url)
    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    target_concepts = {
        "Revenues": "营业收入",
        "NetIncomeLoss": "净利润",
        "StockholdersEquity": "股东权益",
    }

    for concept, cn_desc in target_concepts.items():
        if concept not in us_gaap:
            print(f"\n❌ {concept} ({cn_desc}) 不存在")
            continue

        units = us_gaap[concept].get("units", {})
        if "USD" not in units:
            print(f"\n❌ {concept} 没有 USD 单位")
            continue

        usd_facts = units["USD"]

        # 1) 统计 2024 年后的 fp 取值分布
        recent = [f for f in usd_facts if f.get("end", "") >= "2024-01-01"]
        fp_counter = defaultdict(int)
        for f in recent:
            fp_counter[f.get("fp")] += 1

        print(f"\n📊 {concept} ({cn_desc})")
        print(f"   2024年后 fact 数: {len(recent)}")
        print(f"   fp 取值分布: {dict(fp_counter)}")

        # 2) 检查是否有显式 Q4 单季
        q4_facts = [f for f in recent if f.get("fp") == "Q4"]
        if q4_facts:
            print(f"   ✅ 存在 fp=Q4 单季值！最近一条:")
            latest_q4 = max(q4_facts, key=lambda x: x["end"])
            print(f"      end={latest_q4['end']} val={latest_q4['val']:,} filed={latest_q4['filed']}")
        else:
            print(f"   ⚠️  不存在 fp=Q4 单季值，需要 FY - Q1 - Q2 - Q3 倒推")

        # 3) 打印最近 6 条 fact 的明细
        recent_sorted = sorted(recent, key=lambda x: x["end"])[:6]
        print(f"   最近 6 条 fact 明细:")
        for f in recent_sorted:
            end = f.get("end", "")
            fp = f.get("fp") or ""
            form = f.get("form", "")
            val = f.get("val")
            val_str = f"{val:>18,}" if isinstance(val, (int, float)) else f"{str(val):>18}"
            print(f"      {end:<12} {form:<5} {fp:<5} {val_str}")


if __name__ == "__main__":
    # 默认测几家代表性公司
    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["MSFT", "JPM", "NFLX", "GOOGL"]
    for tk in tickers:
        try:
            probe_company(tk)
        except Exception as e:
            print(f"\n❌ {tk} 探查失败: {e}")
