---
name: fundamentals_analyst
kind: core
description: "Fundamental analysis across four data sources: company overview, balance sheet, cash flow, and income statement. Produces a comprehensive fundamental report with a Markdown summary table."
requires: []
produces:
  - fundamentals_report
capabilities:
  - financial_statement_analysis
  - valuation_metrics
  - balance_sheet_review
  - cash_flow_analysis
  - income_statement_review
best_for:
  - 评估公司财务健康与估值
  - 分析盈利质量、现金流、负债结构
  - 为多空辩论提供基本面证据
not_for:
  - 纯技术面判断
  - 短期情绪捕捉
  - 事件驱动分析（由 news_analyst 负责）
---

# Fundamentals Analyst Skill

对给定 ticker 做基本面分析：拉取公司概览、资产负债表、现金流量表、利润表，
综合判断财务健康、盈利能力、估值水平与现金流质量，输出带 Markdown 汇总表的详细报告。

## Inputs

- `ticker`（必填）：股票代码，如 `AAPL`、`0700.HK`
- `end_date`（必填）：分析截止日，`YYYY-MM-DD`
- `api_key`（可选）：Financial Datasets API Key

## Output

写入 Artifact 的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `fundamentals_report` | `str` | Markdown 基本面报告（含表格） |
| `messages` | `List[BaseMessage]` | 仅最终 AI 消息 |

## Workflow

1. 调用 `get_fundamentals` 拉取公司概览与综合财务指标
2. 调用 `get_balance_sheet` 拉取季度资产负债表
3. 调用 `get_cashflow` 拉取季度现金流量表
4. 调用 `get_income_statement` 拉取季度利润表
5. 交叉分析：盈利质量、现金流、负债、估值、成长性
6. 产出带表格的 Markdown 报告
7. 数据稀疏时明确写 "insufficient data"，不重试

## Notes

- 工具调用上限：4 个工具各 1 次
- 压缩器：`token_budget=4000`（4 个工具内部均有 compress，预算最小但触发最频繁）
- ⚠️ 已知行为：4 个工具内部调用 `compress(text, state=None)`，压缩器走**模块级全局 `CompressionState`**；多 skill 串行时，上一 skill 的 `consumed_tokens` 可能残留影响本 skill 首次压缩判定（详见 skill.py 注释）
