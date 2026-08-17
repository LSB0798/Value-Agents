---
name: warren_buffett_analyst
description: "Analyzes a stock using Warren Buffett's investment principles including moat strength, management quality, intrinsic value, and margin of safety. Best suited for mature, profitable companies with long operating histories."
---

# Warren Buffett Skill

Use this skill when you need a value-oriented, long-term investment analysis focused on business quality and fair pricing. This is especially useful for blue-chip stocks, established companies, and situations where you want to assess whether a business has a durable competitive advantage.

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
| `reasoning` | Detailed rationale in Buffett's style |

```json
{
  "ticker": "AAPL",
  "signal": "bullish",
  "confidence": 85,
  "reasoning": "The company exhibits strong ROE of 35%, consistent earnings growth, and a durable competitive advantage. Trading at a 20% discount to conservative intrinsic value of $200."
}
```

## Workflow

1. **Fetch financial metrics for the past 10 quarters (TTM):**
   - ROE, ROIC, gross margin, operating margin, net margin
   - Debt-to-equity, current ratio, interest coverage
   - Revenue growth, earnings growth, book value growth

2. **Gather line items (annual data, 5-10 periods):**
    - Revenue, net income, EPS, FCF, capex, depreciation
    - Total debt, cash, shareholders equity, outstanding shares
    - R&D spending, buybacks/dividends

3. **Analyze moat strength (40% weight):**
    - Consistency of ROE/ROIC (>15% in 80%+ periods)
    - Pricing power (stable/improving gross margins)
    - Capital intensity (low capex-to-revenue ratio)
    - Intangible assets (brand value from R&D and goodwill)

4. **Evaluate management quality (30% weight):**
    - Capital allocation (FCF-to-net-income ratio > 0.9)
    - Debt management (D/E < 0.5 for excellent, < 1.0 for acceptable)
    - Insider alignment (net insider buying or stable share count)
    - Shareholder friendliness (dividends, buybacks)

5. **Calculate intrinsic value using owner earnings DCF:**
    - Owner earnings = Net Income + Depreciation - Maintenance CapEx - Δ Working Capital
    - Stage 1 (5 years): Conservative growth (capped at 8%)
    - Stage 2 (5 years): Fading growth to terminal
    - Terminal growth: 2.5% (long-term GDP growth)
    - Discount rate: 10% (Buffett's opportunity cost)
    - Apply 15% haircut for conservatism

6. **Determine margin of safety:**
    - Margin of Safety = (Intrinsic Value - Market Cap) / Market Cap
    - 30%: Strong buy (bullish)
    - 10-30%: Attractive (bullish)
    - 0-10%: Fair value (neutral)
    - < 0%: Overvalued (bearish)

7. **Generate final signal with confidence based on:**
    - Quality of the business (moat + management scores)
    - Size of the margin of safety
    - Strength of the growth trajectory

## Notes
  - This skill emphasizes long-term compounding over short-term momentum.
  - It is most suitable for mature, profitable companies with predictable earnings.
  - In Buffett's words: "Price is what you pay, value is what you get."
  - The skill uses a conservative DCF with multiple layers of margin of safety.
  - When uncertain, it defaults to "neutral" rather than taking a speculative stance.