---
name: technical_analyst
description: "Analyzes a stock using technical indicators: trend following, mean reversion, momentum, volatility, and statistical arbitrage. Uses price and volume data to generate trading signals."
best_for:
  - price-based timing and trend analysis
  - momentum and mean reversion setups
  - volatility regime detection
not_for:
  - fundamental or valuation analysis
  - long-term intrinsic value
  - news or sentiment-driven moves
capabilities:
  - trend_following_signal
  - mean_reversion_signal
  - momentum_signal
  - volatility_regime
  - stat_arb_signal
---

# Technical Analyst Skill

Use this skill when you need a quantitative, price-based analysis focusing on market timing, trend direction, and volatility regimes. This is especially useful for short-to-medium term trading decisions.

## Inputs

- `ticker`: Stock symbol (e.g., AAPL, MSFT, KO)
- `start_date`: Start date for historical price data in YYYY-MM-DD format
- `end_date`: End date for analysis in YYYY-MM-DD format
- `api_key`: (Optional) Financial datasets API key. If not provided, the system will attempt to use environment variables.

## Output

Returns a JSON object with the following structure:

| Field | Description |
|-------|-------------|
| `signal` | One of "bullish", "bearish", or "neutral" |
| `confidence` | Confidence score from 0 to 100 |
| `reasoning` | Detailed breakdown of signals from each sub-strategy |

```json
{
  "ticker": "AAPL",
  "signal": "bullish",
  "confidence": 72,
  "reasoning": "Trend following: bullish (ADX 25). Mean reversion: neutral. Momentum: bullish (1-month return +5%). Volatility: neutral. Stat arb: bullish. Combined signal: bullish with 72% confidence."
}
```

## Workflow

1. **Fetch historical price data (OHLCV) for the given date range using get_prices.**

2. **Calculate five categories of technical signals:**
    - Trend Following (25% weight): EMAs (8, 21, 55) and ADX. Bullish if short > medium > long.
    - Mean Reversion (20% weight): Z-score vs 50-day MA, Bollinger Bands position, RSI (14 & 28). Bullish if oversold.
    - Momentum (25% weight): 1-month, 3-month, 6-month returns with volume confirmation.
    - Volatility (15% weight): Historical volatility regime (low vol = bullish for mean reversion, high vol = cautious).
    - Statistical Arbitrage (15% weight): Hurst exponent, skewness, kurtosis. Mean-reverting signals if Hurst < 0.4.

3. **Combine signals using weighted average to produce final signal and confidence.**

4. **Generate final signal with confidence reflecting the strength and consistency of sub-strategies.**

## Notes
  - This skill is purely price-based; it does not use fundamentals or news.
  - It requires at least 30 days of price data for reliable indicators.
  - Defaults to neutral if insufficient data.
  - The confidence is derived from the weighted average of individual strategy confidences.
  - It is best used in conjunction with fundamental analysis for a complete picture.