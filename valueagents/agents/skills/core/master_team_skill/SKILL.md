---
name: master_team
kind: meta
description: "Runs a selected subset of master analyst skills (Buffett, Munger, Graham, etc.) serially and aggregates their signals into master_analyst_signals."
requires:
  - market_report
  - sentiment_report
  - news_report
  - fundamentals_report
produces:
  - master_analyst_signals
  - master_summary
composes:
  - warren_buffett_analyst
  - charlie_munger_analyst
  - ben_graham_analyst
  # ... 用户实际选中的大师列表
capabilities:
  - multi_master_analysis
  - signal_aggregation
  - conviction_scoring
best_for:
  - "用 Buffett + Munger 分析一下"
  - "多个大师同时看多/看空"
  - 与 4 个基础分析师并列的独立视角
not_for:
  - 只需单一大师（直接调 warren_buffett_analyst）
  - 完整 pipeline（master_team 不产出 research/trader/decision）
---

# Master Team Skill

串行调用用户选中的 N 个大师分析师，聚合它们的 signals。

## Inputs

- `company_of_interest`
- `_config.master_analysts`: 选中的大师列表，如 `["warren_buffett_analyst", "charlie_munger_analyst"]`

## Output

| 字段 | 类型 | 说明 |
|---|---|---|
| `master_analyst_signals` | `dict` | `{master_name: {signal, confidence, reasoning}}` |
| `master_summary` | `str` | 聚合摘要（多少 bullish / bearish / neutral） |

## Notes

- 串行调用（不并发），Phase 6b 才做并发
- 每个大师的 `reasoning` 截断到 500 字符
- 若某个大师失败，记录 `signal=neutral, confidence=0, reasoning="failed: ..."` 不中断
