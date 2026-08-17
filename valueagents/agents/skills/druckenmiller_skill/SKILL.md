---
name: stanley_druckenmiller_analyst
description: "Analyzes a stock using Stanley Druckenmiller's macro-driven, momentum-focused approach: asymmetric risk-reward, growth acceleration, price momentum, sentiment, insider activity, and valuation multiples. Best for identifying high-conviction turning points."
---

# Stanley Druckenmiller Skill

Use this skill when you need a dynamic, growth-oriented analysis that prioritizes momentum, earnings acceleration, and favorable risk-reward setups. This is especially useful for identifying stocks with strong price trends, positive sentiment shifts, and catalysts that could drive significant upside.

## Inputs

- `ticker`: Stock symbol (e.g., AAPL, MSFT, NVDA)
- `end_date`: Analysis end date in YYYY-MM-DD format
- `api_key`: (Optional) Financial datasets API key. If not provided, the system will attempt to use environment variables.

## Output

Returns a JSON object with the following structure:

| Field | Description |
|-------|-------------|
| `signal` | One of "bullish", "bearish", or "neutral" |
| `confidence` | Confidence score from 0 to 100 |
| `reasoning` | Detailed rationale in Druckenmiller's decisive, momentum-focused style |

```json
{
  "ticker": "NVDA",
  "signal": "bullish",
  "confidence": 78,
  "reasoning": "Revenue growth accelerating from 35% to 55% YoY, price momentum up 40% over 6 months. Risk-reward asymmetric with 60% upside potential and only 15% downside risk given strong FCF and low debt. Insider buying and positive sentiment reinforce conviction."
}
```

## Workflow

1. **Fetch financial metrics (annual, 5 periods):**
   - Revenue, EPS, net income, operating income, gross margin, operating margin, FCF, capex, cash, debt, equity, shares, EBIT, EBITDA

2. **Fetch price data (1 year of daily prices) for momentum analysis**

3. **Fetch insider trades and company news for sentiment signals**

4. **Analyze growth & momentum (35% weight):**
    - Revenue CAGR (score 0-3)
    - EPS CAGR (score 0-3)
    - Price momentum (score 0-3)

5. **Analyze risk-reward (20% weight):**
    - Debt-to-equity (score 0-3)
    - Price volatility (score 0-3)

6. **Valuation (20% weight):**
    - P/E, P/FCF, EV/EBIT, EV/EBITDA (each 0-2)

7. **Sentiment (15% weight):**
    - News sentiment (score 0-2)

8. **Insider activity (10% weight):**
    - Net insider buying ratio (score 0-2)

9. **Aggregate score (max 10):**
    - = 7.5 → Bullish
    - <= 4.5 → Bearish
    - Otherwise → Neutral

10. **Generate final signal with confidence reflecting conviction.**

## Notes
  - This skill emphasizes growth acceleration and price momentum.
  - It is willing to pay higher valuations for exceptional growth.
  - Insider activity and sentiment serve as important confirmation signals.
  - When data is insufficient, it defaults to neutral with low confidence.