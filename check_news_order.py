import json
import os
from collections import Counter

from valueagents.default_config import DEFAULT_CONFIG

# ---------- 定位文件 ----------
news_dir = os.path.join(DEFAULT_CONFIG["data_cache_dir"], "news")
path = os.path.join(news_dir, "AAPL_news.json")

print("=" * 72)
print(f"检查文件：{path}")
print("=" * 72)

if not os.path.exists(path):
    print(f"❌ 文件不存在：{path}")
    raise SystemExit(1)

# ---------- 读文件 ----------
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"[1] 总条数：{len(data)}")

if not data:
    print("(空文件，无需检查排序)")
    raise SystemExit(0)

# ---------- 日期字段抽取 ----------
dates = [r.get("date", "") for r in data]

# 检测日期格式是否统一
formats = Counter()
for d in dates:
    if len(d) == 10 and d[4] == "-" and d[7] == "-":
        formats["YYYY-MM-DD"] += 1
    elif len(d) >= 8 and d[:8].isdigit():
        formats["YYYYMMDD..."] += 1
    elif not d:
        formats["empty"] += 1
    else:
        formats["other"] += 1

print("\n[2] 日期格式分布：")
for fmt, cnt in formats.most_common():
    print(f"    {fmt}: {cnt} 条")

if len(formats) > 1:
    print("    ⚠️  存在多种日期格式，排序可能不可靠")

# ---------- 排序检查 ----------
print("\n[3] 升序检查（date 从早到晚）")
ascending = True
first_violation = None
violations = []

for i in range(len(data) - 1):
    d_cur = dates[i]
    d_next = dates[i + 1]
    if d_cur > d_next:
        ascending = False
        if first_violation is None:
            first_violation = i
        if len(violations) < 5:
            violations.append(
                (i, d_cur, d_next, data[i].get("title", "")[:50], data[i + 1].get("title", "")[:50])
            )

if ascending:
    print("    ✅ 严格升序")
else:
    print(f"    ❌ 存在 {sum(1 for i in range(len(data)-1) if dates[i] > dates[i+1])} 处逆序")
    print(f"    首个逆序位置：index {first_violation}")
    print("\n    前 5 处逆序示例：")
    for idx, d_cur, d_next, t_cur, t_next in violations:
        print(f"      [{idx}] {d_cur} > {d_next}")
        print(f"           cur : {t_cur}")
        print(f"           next: {t_next}")

# ---------- 降序检查（避免误判方向）----------
descending = all(dates[i] >= dates[i + 1] for i in range(len(dates) - 1))
print(f"\n[4] 是否严格降序：{'✅ 是' if descending else '否'}")
if descending and not ascending:
    print("    ⚠️  当前是降序（从晚到早），与预期相反")

# ---------- 边界展示 ----------
print("\n[5] 首尾对比")
print(f"    首条：[{dates[0]}] {data[0].get('title', '')[:70]}")
print(f"    末条：[{dates[-1]}] {data[-1].get('title', '')[:70]}")

# ---------- 日期覆盖统计 ----------
print("\n[6] 日期分布（前 10 个最早的日期）")
date_counter = Counter(dates)
for d in sorted(date_counter.keys())[:10]:
    print(f"    {d}: {date_counter[d]} 条")

print("\n[7] 日期分布（前 10 个最晚的日期）")
for d in sorted(date_counter.keys(), reverse=True)[:10]:
    print(f"    {d}: {date_counter[d]} 条")

# ---------- 相邻重复 date 检查 ----------
print("\n[8] 相邻记录的同日连续性")
same_day_runs = []
run_start = 0
for i in range(1, len(dates)):
    if dates[i] != dates[i - 1]:
        if i - run_start > 1:
            same_day_runs.append((dates[run_start], i - run_start))
        run_start = i
if len(dates) - run_start > 1:
    same_day_runs.append((dates[run_start], len(dates) - run_start))

if same_day_runs:
    print(f"    发现 {len(same_day_runs)} 段连续同日期块（升序下应如此）")
    for d, cnt in same_day_runs[:5]:
        print(f"      {d}: 连续 {cnt} 条")
else:
    print("    (无连续同日期块)")

# ---------- 最终结论 ----------
print("\n" + "=" * 72)
if ascending and len(formats) == 1:
    print("✅ 排序正确：date 严格升序，格式统一")
elif ascending and len(formats) > 1:
    print("⚠️  排序看起来正确，但日期格式不统一，建议先修复格式")
else:
    print("❌ 排序错误：需要重新排序")
    print("   修复命令：")
    print("   python -m valueagents.agents.utils.process_local_news AAPL")
print("=" * 72)