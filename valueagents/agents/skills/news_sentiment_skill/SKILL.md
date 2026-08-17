---
name: news_sentiment_analyst
description: "Analyzes recent news sentiment for a stock using LLM-based classification of headlines. Returns a bullish/bearish/neutral signal based on the balance of positive vs negative news, with confidence derived from article counts and LLM confidence scores."
---

# News Sentiment Skill

Use this skill when you need a quick, data-driven pulse on market sentiment toward a stock based on recent news headlines. It's especially useful for gauging short-term sentiment shifts or confirming other fundamental signals.

## Inputs

- `ticker`: Stock symbol (e.g., AAPL, MSFT, KO)
- `end_date`: Analysis end date in YYYY-MM-DD format
- `api_key`: (Optional) Financial datasets API key. If not provided, the system will attempt to use environment variables.

## Output

Returns a JSON object with the following structure:

| Field | Description |
|-------|-------------|
| `signal` | One of "bullish", "bearish", or "neutral" |
| `confidence` | Confidence score from 0 to 100 (based on LLM confidence and article count) |
| `reasoning` | Detailed breakdown of sentiment metrics |

```json
{
  "ticker": "AAPL",
  "signal": "neutral",
  "confidence": 55.0,
  "reasoning": {
    "news_sentiment": {
      "signal": "neutral",
      "confidence": 55.0,
      "metrics": {
        "total_articles": 5,
        "bullish_articles": 2,
        "bearish_articles": 2,
        "neutral_articles": 1,
        "articles_classified_by_llm": 5
      }
    }
  }
}
```

## Workflow

1. **Fetch news articles for the ticker over the past 7 days (via get_news tool).**

2. **Parse articles from Markdown format into structured list.**

3. **Select up to 5 most recent articles for sentiment analysis.**

4. **For each article, call the LLM with a sentiment classification prompt:**
    - Prompt: "Analyze sentiment of headline for stock {ticker}. Return JSON with sentiment (positive/negative/neutral) and confidence (0-100)."

5. **Aggregate signals:**
    - Count bullish (positive), bearish (negative), and neutral articles.
    - Determine overall signal by majority vote (ties → neutral).

6. **Calculate confidence:**
    - If LLM confidences available: 0.7 * avg_confidence + 0.3 * (dominant_count / total_count) * 100
    - Otherwise: (dominant_count / total_count) * 100

7. **Generate final signal with detailed reasoning including counts.**

## Notes
  - This skill relies on Alpha Vantage's news API (requires ALPHA_VANTAGE_API_KEY).
  - Only headlines are classified; full article text is not used.
  - The analysis looks back 7 days; limited to 5 articles to control cost and speed.
  - If no articles are found, signal defaults to neutral with 0 confidence.
  - Confidence reflects both LLM certainty and signal dominance.