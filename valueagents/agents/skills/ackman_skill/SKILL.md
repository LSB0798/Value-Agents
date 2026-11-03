---
name: bill_ackman_analyst
description: "Analyzes a stock using Bill Ackman's investment principles: business quality, financial discipline, activism potential, and intrinsic value with margin of safety. Best for identifying high-conviction, long-term opportunities with catalyst potential."
best_for:
  - high-quality consumer and service brands
  - businesses with governance or operational catalyst
  - concentrated long-term value bets
not_for:
  - early-stage speculative companies
  - deep cyclical or commodity businesses
  - pure momentum or sentiment trades
capabilities:
  - business_quality_score
  - intrinsic_value_dcf
  - activism_potential_assessment
  - capital_discipline_review
---

# Bill Ackman Skill

Use this skill when you need a concentrated, high-conviction investment analysis focused on quality businesses with durable moats, strong free cash flow, and potential for operational or governance improvements through activism. This is especially useful for well-known brands with temporary challenges.

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
| `reasoning` | Detailed rationale in Ackman's analytical, confident style |

```json
{
  "ticker": "AAPL",
  "signal": "bullish",
  "confidence": 75,
  "reasoning": "Apple demonstrates a wide economic moat through its ecosystem and brand loyalty. With consistent revenue growth, high margins, and strong FCF generation, the company is a high-quality business. The current valuation offers a 20% margin of safety to our DCF-derived intrinsic value, and management's capital allocation is disciplined. Activism potential is limited as operations are already efficient, but the long-term growth outlook remains attractive."
}
```

## Workflow

1. **Fetch financial metrics (annual, 5 periods):**
   - Revenue, operating margin, debt-to-equity, free cash flow, total assets, total liabilities, dividends, outstanding shares

2. **Analyze business quality (score 0-8):**
    - Revenue growth > 50% cumulative (score 0-2)
    - Operating margins > 15% consistently (score 0-2)
    - ROE > 15% (score 0-2)
    - Positive FCF majority of periods (score 0-1)
    - Intangible assets (optional, score 0-1)

3. **Analyze financial discipline (score 0-4):**
    - Debt-to-equity < 1.0 majority of periods (score 0-2)
    - Dividend track record (score 0-1)
    - Share count decreasing over time (buybacks) (score 0-1)

4. **Analyze activism potential (score 0-2):**
    - Revenue growth > 15% but operating margins < 10% (score +2)

5. **Perform valuation (score 0-4):**
    - Simple DCF with FCF (5-year projection, 6% growth, 10% discount, 15x terminal multiple)
    - Margin of safety > 30% (score +3), > 10% (score +1)

6. **Aggregate scores:**
    - Max possible score = 20 (8+4+2+4)
    - Bullish if >= 70% of max, Bearish if <= 30%, Neutral otherwise

7. **Generate final signal with confidence reflecting the strength of the investment case.**

## Notes
  - This skill emphasizes quality over cheapness; Ackman is willing to pay a fair price for a great business.
  - It looks for catalysts that can unlock value (activism, management change, operational improvements).
  - The analysis uses annual data to capture long-term trends.
  - When data is insufficient, it defaults to neutral with low confidence.