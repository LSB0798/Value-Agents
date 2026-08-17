---
name: sentiment_analyst
description: "Analyzes market sentiment by combining insider trading signals (30%) and news sentiment (70%). Provides a weighted overall signal with confidence score. Best for understanding market psychology and sentiment-driven price movements."
---

# Sentiment Analyst Skill

Use this skill when you need to assess market sentiment and crowd psychology for a stock. It combines two key sentiment indicators: insider trading activity (what company insiders are doing) and news sentiment (how the media and market are reacting to company developments). This is especially useful for identifying potential contrarian opportunities or momentum signals.

## Inputs

- `ticker`: Stock symbol (e.g., AAPL, MSFT, KO)
- `end_date`: Analysis end date in YYYY-MM-DD format
- `api_key`: (Optional) Financial datasets API key. If not provided, the system will attempt to use environment variables.

## Output

Returns a JSON object with the following structure:

| Field | Description |
|-------|-------------|
| `signal` | One of "bullish", "bearish", or "neutral" |
| `confidence` | Confidence score from 0 to 100 |
| `reasoning` | Detailed breakdown of insider and news sentiment components |

```json
{
  "ticker": "AAPL",
  "signal": "bullish",
  "confidence": 62.4,
  "reasoning": {
    "insider_trading": {
      "signal": "bullish",
      "confidence": 62,
      "metrics": {...}
    },
    "news_sentiment": {
      "signal": "neutral",
      "confidence": 0,
      "metrics": {...}
    },
    "combined_analysis": {
      "total_weighted_bullish": 21.9,
      "total_weighted_bearish": 13.2,
      "signal_determination": "Bullish based on weighted signal comparison"
    }
  }
}
```

## Workflow

1. **Fetch insider trades (last 1000 transactions, up to 1 year back):**
    - Transaction shares: negative = selling ("bearish"), positive = buying ("bullish")
    -   Weight: 30% of final signal

2. **Fetch company news (last 100 articles):**
    - Sentiment: "positive" = bullish, "negative" = bearish, "neutral" = neutral
    - Weight: 70% of final signal

3. **Calculate weighted signals:**
    - Weighted bullish = (bullish insider trades count × 0.3) + (bullish news articles × 0.7)
    - Weighted bearish = (bearish insider trades count × 0.3) + (bearish news articles × 0.7)

4. **Determine overall signal:**
    - If weighted bullish > weighted bearish: "bullish"
    - If weighted bearish > weighted bullish: "bearish"
    - Otherwise: "neutral"

5. **Calculate confidence:**
    - Confidence = (max(weighted bullish, weighted bearish) / total weighted signals) × 100

6. **Generate detailed reasoning with breakdown of both components.**

## Notes
  - This skill is data-driven and does not rely on LLM reasoning for signal generation.
  - The signal is purely based on quantitative sentiment indicators.
  - Insider trading data is sourced from Finnhub, news sentiment from Alpha Vantage.
  - Requires both FINNHUB_API_KEY and ALPHA_VANTAGE_API_KEY for full functionality.
  - If one data source is unavailable, the remaining source's weight is effectively increased.
  - When no signals are available, returns neutral with 0 confidence.