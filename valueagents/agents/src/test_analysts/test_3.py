#!/usr/bin/env python
"""
Step 3: 只看 2024-01-01 以后的 fact，确认近期数据是否完整。
极简脚本，只打印，不做任何转换/差分/对齐。
"""
import requests

USER_AGENT = "ValueAgents research your_email@example.com"  # ← 改成你自己的邮箱
CIK = "0000320193"  # AAPL
URL = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"


def _get_json(url: str) -> dict:
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def step3_explore_recent():
    data = _get_json(URL)
    us_gaap = data.get("facts", {}).get("us-gaap", {})

    target_concepts = [
        "Revenues",
        "NetIncomeLoss",
        "StockholdersEquity",
    ]

    for concept in target_concepts:
        if concept not in us_gaap:
            print(f"\n❌ {concept} 不存在")
            continue

        concept_data = us_gaap[concept]
        label = concept_data.get("label") or "(no label)"
        units = concept_data.get("units", {})

        print(f"\n{'='*110}")
        print(f"概念: {concept}")
        print(f"  label: {label}")

        for unit, facts_list in units.items():
            if unit != "USD":
                continue

            # ✅ 核心过滤：只看 end >= 2024-01-01 的 fact
            recent = [f for f in facts_list if f.get("end", "") >= "2024-01-01"]

            # 按 end 倒序、filed 倒序（同 end 取最新 filed 的放前面）
            recent_sorted = sorted(recent, key=lambda x: (x["end"], x["filed"]), reverse=True)

            print(f"  📌 {concept} [{unit}] end>=2024-01-01 共 {len(recent_sorted)} 条 fact:")
            print(f"     {'end':<12} {'form':<5} {'fp':<5} {'val':>18} {'filed':<12} {'start':<12}")
            print(f"     {'-'*75}")

            for f in recent_sorted:
                end = f.get("end", "")
                form = f.get("form", "")
                fp = f.get("fp") or ""
                val = f.get("val")
                filed = f.get("filed", "")
                start = f.get("start", "")
                val_str = f"{val:>18,}" if isinstance(val, (int, float)) else f"{str(val):>18}"
                print(f"     {end:<12} {form:<5} {fp:<5} {val_str} {filed:<12} {start:<12}")

            # 统计 fp 取值（过滤 None）
            fp_values = sorted(set(f.get("fp") for f in recent if f.get("fp")))
            print(f"\n  📊 {concept} (2024+) fp 取值: {fp_values}")

            # 检查是否有 Q4 单季值
            q4_facts = [f for f in recent if f.get("fp") == "Q4"]
            if q4_facts:
                print(f"  ✅ 存在 fp=Q4 的单季值:")
                for f in q4_facts:
                    print(f"     end={f['end']} val={f['val']:,}")
            else:
                print(f"  ⚠️  不存在 fp=Q4 的单季值（需用 FY - Q1-Q2-Q3 倒推）")

            # 检查 FY 全年值
            fy_facts = [f for f in recent if f.get("fp") == "FY"]
            if fy_facts:
                print(f"  📌 存在 fp=FY 的全年累计值:")
                for f in fy_facts:
                    print(f"     end={f['end']} val={f['val']:,}")

            # 检查 restatement（同 end 多条）
            from collections import Counter
            end_counts = Counter(f.get("end") for f in recent)
            dup = {e: c for e, c in end_counts.items() if c > 1}
            if dup:
                print(f"  🔁 restatement（同 end 多条）: {dup}")


if __name__ == "__main__":
    step3_explore_recent()
