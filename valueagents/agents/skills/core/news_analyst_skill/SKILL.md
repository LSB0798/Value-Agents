---
name: news_analyst
kind: core
description: "Company-specific news flow plus global macro news. Produces a news & macro intelligence report with event-driven and macroeconomic context."
requires: []
produces:
  - news_report
capabilities:
  - event_driven_analysis
  - macro_context
  - company_news_scan
  - global_news_scan
best_for:
  - 评估事件驱动风险与催化剂
  - 判断宏观环境对个股的影响
  - 为多空辩论提供新闻面证据
not_for:
  - 纯技术面判断
  - 财务估值
  - 社交舆情（由 social_analyst 负责）
---

# News Analyst Skill

对给定 ticker 做新闻与宏观分析：拉取最近一周的公司新闻与全球宏观新闻，
综合判断事件驱动、宏观背景、潜在催化剂，输出带 Markdown 汇总表的详细报告。

## Inputs

- `ticker`（必填）：股票代码，如 `AAPL`、`0700.HK`
- `end_date`（必填）：分析截止日，`YYYY-MM-DD`
- `api_key`（可选）：Financial Datasets API Key

## Output

写入 Artifact 的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `news_report` | `str` | Markdown 新闻/宏观报告（含表格） |
| `messages` | `List[BaseMessage]` | 仅最终 AI 消息 |

## Workflow

1. 调用 `get_news(ticker, start_date, end_date)` 拉取 `[end_date-7, end_date]` 窗口内的公司新闻
2. 调用 `get_global_news(curr_date, look_back_days, limit)` 拉取宏观新闻
3. 交叉分析：公司层面事件 + 宏观背景 + 潜在催化剂
4. 产出带表格的 Markdown 报告
5. 数据稀疏时明确写 "insufficient data"，不重试

## Notes

- 工具调用上限：1 次 `get_news` + 1 次 `get_global_news`
- 压缩器：`token_budget=25000`（新闻文本长，预算最高）
- 与 `social_analyst` 的分工：news 关注**事件驱动与宏观**，social 关注**公众情绪与叙事**
- 已知外部依赖风险：`get_global_news` 底层聚合 GNews/Finnhub/AlphaVantage，GNews 429 时可能返回空
