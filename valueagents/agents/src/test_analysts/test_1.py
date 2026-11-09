#!/usr/bin/env python
"""
Step 2: 探查 AAPL 核心财务字段的原始 XBRL fact 结构。
只打印，不做任何转换/差分/对齐，避免引入 bug。
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

    # 要探查的核心字段
    target_concepts = [
        "Revenues",
        "NetIncomeLoss",
        "StockholdersEquity",
    ]

    for concept in target_concepts:
        if concept not in us_gaap:
            print(f"\n❌ {concept} 不存在于 AAPL 的 XBRL 中")
            continue

        concept_data = us_gaap[concept]
        # label 可能为 None，用 or 兜底
        label = concept_data.get("label") or "(no label)"
        units = concept_data.get("units", {})

        print(f"\n{'='*100}")
        print(f"概念: {concept}")
        print(f"  label: {label}")
        print(f"  可用单位: {list(units.keys())}")

        # 对每个单位打印最近 12 条 fact
        for unit, facts_list in units.items():
            if unit != "USD":
                continue  # 先看 USD 单位

            # 按 end 日期倒序，取最近 12 条
            facts_sorted = sorted(facts_list, key=lambda x: x["end"], reverse=True)
            recent = facts_sorted[:12]

            print(f"\n  📌 {concept} [{unit}] 最近 12 条 fact (按 end 倒序):")
            print(f"     {'end':<12} {'form':<5} {'fp':<5} {'val':>18} {'filed':<12} {'has_start':<10}")
            print(f"     {'-'*70}")

            for f in recent:
                end = f.get("end")
                form = f.get("form")
                fp = f.get("fp")
                val = f.get("val")
                filed = f.get("filed")
                has_start = "start" in f  # duration 才有 start

                val_str = f"{val:>18,}" if isinstance(val, (int, float)) else f"{str(val):>18}"
                print(f"     {end:<12} {form:<5} {fp:<5} {val_str} {filed:<12} {str(has_start):<10}")

            # 额外统计：这个 concept 下 fp 字段有哪些不同取值
            fp_values = set(f.get("fp") for f in facts_list)
            print(f"\n  📊 {concept} 所有 fp 取值: {sorted(fp_values)}")

            # 检查财年末（September）有没有 fp=Q4 的单季值
            sep_facts = [f for f in facts_list if f.get("end", "").startswith("2024-09") or f.get("end", "").startswith("2025-09")]
            if sep_facts:
                print(f"  🔍 2024-09 / 2025-09 的 fact:")
                for f in sep_facts:
                    print(f"     end={f['end']} form={f['form']} fp={f.get('fp')} val={f['val']:,}")


if __name__ == "__main__":
    step2_explore_core_fields()