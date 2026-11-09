---
name: social_analyst
kind: core
description: "Social media & company-specific sentiment analysis. Scans recent news and public discussion to gauge market sentiment and narrative momentum."
requires: []
produces:
  - sentiment_report
capabilities:
  - social_sentiment
  - narrative_tracking
  - retail_sentiment
  - news_flow
best_for:
  - 判断市场情绪与叙事方向
  - 捕捉短期舆情拐点
  - 辅助多空辩论的情绪面证据
not_for:
  - 纯技术面判断
  - 财务估值
  - 长期基本面分析
---

# Social Analyst Skill

对给定 ticker 做社交舆情与公司新闻情绪分析：拉取最近一周的新闻/讨论，
综合判断市场情绪、叙事方向、公众预期，输出带 Markdown 汇总表的详细报告。

## Inputs

- `ticker`（必填）：股票代码，如 `AAPL`、`0700.HK`
- `end_date`（必填）：分析截止日，`YYYY-MM-DD`
- `api_key`（可选）：Financial Datasets API Key

## Output

写入 Artifact 的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `sentiment_report` | `str` | Markdown 情绪报告（含表格） |
| `messages` | `List[BaseMessage]` | 仅最终 AI 消息 |

## Workflow

1. 调用 `get_news` 拉取 `[end_date-7, end_date]` 窗口内的公司新闻与讨论
2. 逐条阅读标题与摘要，识别正/负面信号与叙事主题
3. 综合判断短期情绪、公众预期、叙事拐点
4. 产出带表格的 Markdown 报告
5. 数据稀疏时明确写 "insufficient data"，不重试、不换窗口

## Notes

- 工具调用上限：1 次 `get_news`
- 压缩器：`token_budget=20000`（新闻文本较长，预算高于 market）
- 与 `news_analyst` 的分工：social 关注**公众情绪与叙事**，news 关注**宏观与事件驱动**
