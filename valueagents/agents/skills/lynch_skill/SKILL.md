---
name: peter_lynch_analyst
description: "Analyzes a stock using Peter Lynch's GARP (Growth at a Reasonable Price) framework: revenue/EPS growth, PEG ratio, debt levels, and insider activity. Best for identifying 'ten-bagger' opportunities in understandable businesses."
best_for:
  - GARP via PEG ratio
  - understandable consumer businesses
  - potential ten-bagger candidates
not_for:
  - overly complex or opaque businesses
  - highly leveraged companies
  - deep-value asset plays
capabilities:
  - peg_ratio_analysis
  - revenue_eps_growth
  - fundamentals_check
  - insider_sentiment
---

# Peter Lynch Skill

Use this skill when you need a growth-oriented, common-sense investment analysis focused on companies you can understand, with strong earnings growth at a reasonable price. This is especially useful for identifying potential "ten-baggers" (stocks that can rise 10x) and avoiding overly complex or highly leveraged businesses.

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
| `reasoning` | Detailed rationale in Peter Lynch's folksy, practical style |

```json
{
  "ticker": "AAPL",
  "signal": "neutral",
  "confidence": 45,
  "reasoning": "Apple shows steady revenue and EPS growth, with a PEG ratio of 1.8 and manageable debt. The business is understandable and has strong margins. However, the stock is not a bargain—it's fairly priced. If my kids keep buying iPhones, I'd watch for a pullback to get more attractive."
}
```

## Workflow

1. **Fetch financial line items (annual, 5 periods):**
    - Revenue, earnings per share, net income, operating income
    - Gross margin, operating margin, free cash flow, capex
    - Cash, total debt, shareholders equity, outstanding shares

2. **Fetch market cap (current):**
    - Used for valuation calculations (P/E, PEG)

3. **Fetch insider trades (50 recent):**
    - Insider buying/selling activity (score 0-8)

4. **Fetch company news (50 recent):**
    - Sentiment analysis via keyword detection (score 0-8)

5. **Analyze growth (score 0-10, 30% weight):**
    - Revenue growth rate: >25% (+3), >10% (+2), >2% (+1)
    - EPS growth rate: >25% (+3), >10% (+2), >2% (+1)

6. **Analyze valuation - PEG ratio (score 0-10, 25% weight):**
    - Calculate P/E = market cap / net income
    - Calculate EPS growth rate (CAGR over 5 years)
    - PEG = P/E / (EPS growth rate × 100)
    - PEG < 1: Very attractive (+3), < 2: Good (+2), < 3: Fair (+1)
    - P/E < 15: (+2), < 25: (+1)

7. **Analyze fundamentals (score 0-10, 20% weight):**
    - Debt-to-equity < 0.5: (+2), < 1.0: (+1)
    - Operating margin > 20%: (+2), > 10%: (+1)
    - Positive free cash flow: (+2)

8. **Analyze sentiment (score 0-10, 15% weight):**
    - Negative headlines > 30%: score 3
    - Some negative headlines: score 6
    - Mostly positive: score 8

9. **Analyze insider activity (score 0-10, 10% weight):**
    - Buy ratio > 70%: score 8
    - Buy ratio > 40%: score 6
    - Mostly selling: score 4

10. **Generate final signal:**
    - Weighted score: (Growth × 0.30) + (Valuation × 0.25) + (Fundamentals × 0.20) + (Sentiment × 0.15) + (Insider × 0.10)
    - Bullish if score >= 7.5, Bearish if <= 4.5, Neutral otherwise

## Notes
  - This skill emphasizes "Invest in what you know" - businesses with simple, understandable models.
  - Lynch likes companies with steady, consistent growth and low debt.
  - The PEG ratio is the single most important metric in this analysis.
  - "Ten-bagger" potential is evaluated through growth runway and valuation.
  - When uncertain, it defaults to neutral with low confidence.