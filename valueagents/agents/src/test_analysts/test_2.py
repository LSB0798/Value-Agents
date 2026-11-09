#!/usr/bin/env python
"""
Step 2 (修复版): 探查 AAPL 核心财务字段的原始 XBRL fact 结构。
修复：fp 可能为 None 导致 sorted 报错。
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


def step2_explore_core_fields():
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

        print(f"\n{'='*100}")
        print(f"概念: {concept}")
        print(f"  label: {label}")
        print(f"  可用单位: {list(units.keys())}")

        for unit, facts_list in units.items():
            if unit != "USD":
                continue

            facts_sorted = sorted(facts_list, key=lambda x: x["end"], reverse=True)
            recent = facts_sorted[:12]

            print(f"\n  📌 {concept} [{unit}] 最近 12 条 fact:")
            print(f"     {'end':<12} {'form':<5} {'fp':<5} {'val':>18} {'filed':<12} {'start':<12}")
            print(f"     {'-'*75}")

            for f in recent:
                end = f.get("end", "")
                form = f.get("form", "")
                fp = f.get("fp") or ""
                val = f.get("val")
                filed = f.get("filed", "")
                start = f.get("start", "")
                val_str = f"{val:>18,}" if isinstance(val, (int, float)) else f"{str(val):>18}"
                print(f"     {end:<12} {form:<5} {fp:<5} {val_str} {filed:<12} {start:<12}")

            # ✅ 修复：过滤 None 再排序
            fp_values = set(f.get("fp") for f in facts_list)
            fp_clean = sorted([x for x in fp_values if x is not None])
            print(f"\n  📊 {concept} 所有 fp 取值: {fp_clean}")

            # 统计每个 end 日期有多少条记录（检测 restatement）
            from collections import Counter
            end_counts = Counter(f.get("end") for f in facts_list)
            dup_ends = {e: c for e, c in end_counts.items() if c > 1}
            if dup_ends:
                print(f"  🔁 有 restatement 的 end 日期: {dup_ends}")

            # 检查 2024-09 / 2025-09 是否有 Q4 单季值
            sep_facts = [
                f for f in facts_list
                if f.get("end", "").startswith("2024-09") or f.get("end", "").startswith("2025-09")
            ]
            if sep_facts:
                print(f"  🔍 2024-09 / 2025-09 的 fact:")
                for f in sep_facts:
                    print(f"     end={f['end']} form={f['form']} fp={f.get('fp')} val={f['val']:,}")


if __name__ == "__main__":
    step2_explore_core_fields()
