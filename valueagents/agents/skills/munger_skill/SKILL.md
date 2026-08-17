---
name: charlie_munger_analyst
description: "Analyzes a stock using Charlie Munger's mental models: moat strength, management quality, business predictability, and valuation with margin of safety. Best for identifying high-quality, predictable businesses with durable competitive advantages."
---

# Charlie Munger Skill

Use this skill when you need a rigorous, multi-disciplinary analysis focused on business quality, moat durability, management integrity, and earnings predictability. This is especially useful for identifying wonderful companies that can compound value over the long term.

## Inputs

- `ticker`: Stock symbol (e.g., AAPL, BRK.B, KO)
- `end_date`: Analysis end date in YYYY-MM-DD format
- `api_key`: (Optional) Financial datasets API key. If not provided, the system will attempt to use environment variables.

## Output

Returns a JSON object with the following structure:

| Field | Description |
|-------|-------------|
| `signal` | One of "bullish", "bearish", or "neutral" |
| `confidence` | Confidence score from 0 to 100 |
| `reasoning` | Detailed rationale in Munger's direct, wisdom-filled style |

```json
{
  "ticker": "BRK.B",
  "signal": "bullish",
  "confidence": 78,
  "reasoning": "Berkshire possesses a durable moat through its insurance float and capital allocation. ROIC consistently exceeds 15%, management has demonstrated exceptional capital discipline, and the business is highly predictable. Trading at a 25% discount to our conservative intrinsic value estimate."
}
```

## Workflow

1. **Fetch financial metrics (annual, 10 periods):**
   - Revenue, net income, operating income, ROIC, gross margin, operating margin, FCF, capex, cash, debt, equity, shares, R&D, goodwill

2. **Fetch insider trades (100 records):**
    - Insider buying/selling activity (Munger values skin in the game)

3. **Fetch company news (10 articles):**
    - Recent news and sentiment (Munger avoids troubled businesses)

4. **Analyze moat strength (35% weight, score 0-10):**
    - ROIC consistency (>15% in 80%+ periods) (score 0-3)
    - Pricing power (stable/improving gross margins) (score 0-2)
    - Low capital intensity (capex/revenue < 5%) (score 0-2)
    - Intangible assets (R&D, goodwill, brand value) (score 0-2)

5. **Analyze management quality (25% weight, score 0-10):**
    - Cash conversion (FCF/NI ratio) (score 0-3)
    - Debt management (D/E ratio) (score 0-3)
    - Cash management (cash/revenue 10-25%) (score 0-2)
    - Insider alignment (buy ratio) (score 0-2)
    - Share count discipline (score 0-2)

6. **Analyze business predictability (25% weight, score 0-10):**
    - Revenue growth stability (score 0-3)
    - Operating income consistency (score 0-3)
    - Margin stability (score 0-2)
    - FCF consistency (score 0-2)

7. **Perform valuation (15% weight, score 0-10):**
    - Normalized FCF yield (score 0-4)
    - Margin of safety vs. reasonable value (score 0-3)
    - FCF growth trajectory (score 0-3)

8. **Aggregate scores:**
    - Total = moat0.35 + management0.25 + predictability0.25 + valuation0.15
    - Bullish if >= 7.5, Bearish if <= 5.5, Neutral otherwise

9. **Generate final signal with confidence reflecting the strength of the overall assessment.**

## Notes
  - This skill emphasizes quality and predictability above all else.
  - It is most suitable for businesses with simple, understandable models and durable moats.
  - Munger would avoid businesses with volatile earnings, high debt, or questionable management.
  - The analysis uses 10 years of annual data to capture long-term trends.
  - When data is insufficient, it defaults to neutral with low confidence.