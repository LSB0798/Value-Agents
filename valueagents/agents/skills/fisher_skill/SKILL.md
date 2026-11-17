---
name: phil_fisher_analyst
description: "Analyzes a stock using Phil Fisher's growth investing principles: long-term growth potential, management quality, R&D intensity, margins stability, and valuation discipline. Best for identifying quality compounders."
best_for:
  - long-term growth compounders
  - R&D-driven innovation pipelines
  - margin-stable quality businesses
not_for:
  - deep-value asset plays
  - turnarounds or distressed situations
  - short-term trading setups
capabilities:
  - rd_intensity_score
  - growth_quality_metrics
  - margin_stability_analysis
  - management_efficiency_review
---

# Phil Fisher Skill

Use this skill when you need a growth-oriented, quality-focused analysis that emphasizes sustainable competitive advantages, management's capital allocation, and R&D-driven innovation. This is especially useful for identifying companies with long-term compounding potential.

## Inputs

- `ticker`: Stock symbol (e.g., AAPL, MSFT, TSLA)
- `end_date`: Analysis end date in YYYY-MM-DD format
- `api_key`: (Optional) Financial datasets API key. If not provided, the system will attempt to use environment variables.

## Output

Returns a JSON object with the following structure:

| Field | Description |
|-------|-------------|
| `signal` | One of "bullish", "bearish", or "neutral" |
| `confidence` | Confidence score from 0 to 100 |
| `reasoning` | Detailed rationale in Phil Fisher's thorough, growth-focused style |

```json
{
  "ticker": "AAPL",
  "signal": "bullish",
  "confidence": 78,
  "reasoning": "Apple exhibits sustained growth characteristics with revenue CAGR of 12% over five years. Management has demonstrated exceptional capital allocation, and R&D investment of 6% of revenue continues to drive product innovation. Margins remain stable and high, with operating margins consistently above 25%. The company's competitive advantages appear durable, supported by ecosystem lock-in and brand loyalty."
}
```

## Workflow

1. **Fetch financial line items (annual, 5 periods):**
   - Revenue, net income, EPS, FCF, R&D, operating income, operating margin, gross margin, total debt, shareholders equity, cash, EBIT, EBITDA

2. **Fetch market cap:**
    - Current market capitalization from Yahoo Finance

3. **Fetch insider trades:**
    - Insider transactions for sentiment and management alignment

4. **Fetch company news:**
    - Recent news for qualitative sentiment analysis

5. **Analyze growth & quality (weight 30%):**
    - Revenue CAGR (score 0-3): >20% (3), >10% (2), >3% (1)
    - EPS CAGR (score 0-3): >20% (3), >10% (2), >3% (1)
    - R&D as % of revenue (score 0-3): 3-15% (3), >15% (2), >0% (1)

6. **Analyze margins & stability (weight 25%):**
    - Operating margin consistency (score 0-2): stable/improving (2), positive (1)
    - Gross margin level (score 0-2): >50% (2), >30% (1)
    - Operating margin stability (score 0-2): very stable (2), reasonably stable (1)

7. **Analyze management efficiency & leverage (weight 20%):**
    - ROE (score 0-3): >20% (3), >10% (2), >0% (1)
    - Debt-to-equity (score 0-2): <0.3 (2), <1.0 (1)
    - FCF consistency (score 0-1): >80% positive (1)

8. **Perform valuation (weight 15%):**
    - P/E (score 0-2): <20 (2), <30 (1)
    - P/FCF (score 0-2): <20 (2), <30 (1)

9. **Analyze insider activity (weight 5%):**
    - Buy ratio >70% (score 8/10), >40% (6/10), otherwise (4/10)

10. **Analyze sentiment (weight 5%):**
    - News sentiment based on negative keyword analysis

11. **Aggregate scores:**
    - Weighted total_score (max 10)
    - Bullish if >= 7.5, Bearish if <= 4.5, Neutral otherwise

12. **Generate final signal with confidence reflecting the strength of the growth thesis.**

## Notes
  - This skill emphasizes long-term growth potential over current valuation.
  - It is most suitable for companies with strong R&D and innovation track records.
  - Fisher was willing to pay higher multiples for exceptional growth and quality.
  - The analysis uses annual data to capture long-term trends.
  - When data is insufficient, it defaults to neutral with low confidence.