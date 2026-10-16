

# NVDA Technical Analysis Report
**Analysis Date: 2026-07-06 | Current Price: $194.61**

---

## 1. Executive Summary

NVDA is in a **textbook "pullback within an uptrend"** configuration. Over the trailing 12 months, the stock compounded ~27.3% ($152.92 → $194.61), peaked at **$235.20 on May 14, 2026**, and has since corrected ~17% off that high. The technical picture is **divided across timeframes**:

- **Long-term (strategic): Bullish and intact** — price is trading above a steadily rising 200 SMA, and the 50 SMA sits well above it (golden-cross structure preserved).
- **Medium-term (tactical): Corrective** — price is below the 50 SMA and VWMA; MACD is negative.
- **Short-term (entry timing): Early stabilization** — RSI is recovering from near-oversold, the MACD histogram is curling up off its trough, and ATR volatility is contracting.

**Net bias: HOLD** — maintain long exposure (uptrend intact) but do **not** chase; the 190-area support confluence is the high-probability accumulation zone. Add on confirmation (see Section 6).

---

## 2. Indicator Selection Rationale (8 Indicators)

I chose a **non-redundant, multi-timeframe** set to answer the three core questions of a correction-phase trade: *Is the trend intact? Is momentum turning? How should I size/stop?*

| Category | Indicator | Why Selected |
|---|---|---|
| Trend (long) | **close_200_sma** | Strategic benchmark; defines whether the macro uptrend survived the correction |
| Trend (medium) | **close_50_sma** | Dynamic support/resistance; the primary tactical level in a pullback |
| Momentum | **macd** | Confirms trend-change timing via zero-line crossovers |
| Momentum | **macdh** | Early-warning gauge of momentum *acceleration* and divergence |
| Oscillator | **rsi** | Flags the overbought→oversold cycle and reversal potential |
| Volatility | **atr** | Reactive risk measure for stop-loss and position sizing |
| Volatility | **boll_lb** | Identifies the oversold support floor within the volatility envelope |
| Volume | **vwma** | Volume-confirmation filter to validate whether the pullback is healthy vs. distribution |

*Redundancy avoided:* I excluded overlapping MACD components (macds vs. macd/macdh) and paired a single volatility-band member (boll_lb) with ATR rather than stacking all three Bollinger bands.

---

## 3. Detailed Trend Analysis

### 3.1 Trend Structure — Uptrend Intact, but Price Has Broken Below the Medium-Term Average

- **200 SMA: 190.71 (Jul 6)**, up from 179.72 (Apr 7) — a clean, uninterrupted ~6.1% rise over the quarter. At **$194.61, price sits just above the 200 SMA**, confirming the long-term uptrend is **structurally alive**. This is the single most important bullish data point in the dataset: the macro trend has not been invalidated.
- **50 SMA: 209.28 (Jul 6)**, peaking at 209.82 (Jun 24) before a slight, orderly fade. Critically, price ($194.61) is now **~14 points (≈7%) below the 50 SMA** — the classic signature of a correction rather than a new downtrend. The 50 SMA remains far above the 200 SMA, so the **golden-cross architecture is preserved**; only the short-side of the average stack has been breached.

**Interpretation:** The two moving averages form a **bullish spread** (50 SMA > 200 SMA) that has held through the entire correction. The $194.61 price is now testing the *top* of the 200 SMA — a natural bull/bull boundary. As long as price holds above ~190, the medium-term dip is buyable; a decisive close below 190 would degrade the structure toward a full 50/200 alignment.

### 3.2 Momentum — Bearish, but Decelerating (The Most Important Nuance)

This is where the two MACD components diverge meaningfully from a simple "MACD is negative, so sell" read:

- **MACD line: -4.09 (Jul 6)**, down from a +9.31 peak (May 15). It crossed below zero in early June. In isolation this is bearish.
- **MACD Histogram: -0.84 (Jul 6)** — **up sharply from its -2.65 trough (Jun 10)**. The histogram crossed the zero line on **May 21–22** (the true momentum regime change) and has now *stabilized and is curling back toward zero*.

**The histogram is the tell.** A falling MACD line *combined with* a rising histogram = **downward momentum is decelerating**. The selling that drove the stock from $235 → the low-190s is losing steam. We are not seeing accelerating distribution; we are seeing an *exhausting* correction. A bullish momentum reversal is confirmed when the histogram crosses above zero (i.e., MACD crosses above its signal line) — that has not happened yet, hence no aggressive entry.

### 3.3 Oscillator — RSI Confirms Recovery From Oversold

- **RSI: 42.01 (Jul 6)**, having cycled from a **76.72 overbought extreme (May 14)** down to a **37.57 near-oversold trough (Jun 26)**, then recovered ~4.4 points.
- RSI at 42 is **above the 30 oversold floor but below the 50 midline**. This is the "stabilizing but not yet bullish" zone. The move off 37.57 indicates **immediate downside momentum is waning**, but there is no bullish confirmation until RSI reclaims 50.
- Note the **healthy cycle symmetry**: RSI peaked (76.7) and price peaked (May 14) on the *same day*, then RSI troughed (Jun 26) roughly six weeks later — a clean, non-divergent downswing. The absence of a bearish divergence at the top suggests the May top was a momentum exhaustion rather than a fundamental crack.

### 3.4 Volatility — Risk Normalizing (Favorable for Positioning)

- **ATR: 6.86 (Jul 6)**, down from a **peak of 8.55 (Jun 9)** and a low of 4.86 (Apr 22). The stock traded ~3.5 points/true-range at the June panic, now ~6.86 — a **~20% de-escalation from the volatility spike**.
- The June 8–12 window (ATR > 8.0) coincides with the sharpest leg of the decline — likely capitulation/position unwinding. Its passing is constructive: **stops are more reliable now**, and position sizing can be more precise. The contraction from 8.55 → 6.86 typically precedes a directional resolution (breakout or breakdown), so traders should watch the next move closely.

### 3.5 Support Floor — Bollinger Lower Band

- **Bollinger Lower Band: 190.12 (Jul 6)**, down from a 206.93 peak (Jun 4). The current band level sits in a **confluence with the 200 SMA (190.71)** — a rare two-indicator support cluster in the **~190 zone**.
- Price ($194.61) is only **~4.5 points above the lower band**, meaning the volatility envelope is providing a measured floor. A hold here is the trigger for mean-reversion longs; a break below 190 opens the next support reference.

### 3.6 Volume Confirmation — VWMA Has Not Yet Turned (The Caution Flag)

- **VWMA: 201.00 (Jul 6)**, down from a 220.25 peak (Jun 2) — an ~8.7% retreat. Price ($194.61) is **below the VWMA**.
- This is the **key caution in the entire dataset**: while price momentum (MACD histogram) and the oscillator (RSI) are stabilizing, **volume-weighted price is still declining**. A healthy accumulation bottom typically shows the VWMA flattening or rising alongside price. Until the VWMA stabilizes, the correction is technically "unconfirmed" on the volume axis — i.e., we have not yet seen the buying volume that would seal a bottom.

---

## 4. Key Price Levels

| Level | Price | Type | Basis |
|---|---|---|---|
| **Resistance 3** | ~235.20 | Major | May 14, 2026 all-time close high |
| **Resistance 2** | ~209.3–220.3 | Strong | 50 SMA (209.28) + VWMA (201.00) overhead |
| **Resistance 1** | ~201.0 | Moderate | VWMA — first reclaim target |
| **Current** | **194.61** | — | Jul 6 close |
| **Support 1** | **~190.1–190.7** | **Major confluence** | 200 SMA (190.71) + Bollinger LB (190.12) |
| **Support 2** | ~179.7 | Secondary | 200 SMA level from early April / psychological 180 |

The **~190 confluence** is the single most important line in the trade. Holding it keeps the long-term uptrend intact; losing it converts this from a "buy the dip" into a "wait for a base" scenario.

---

## 5. Risk Management

- **Volatility basis:** ATR = 6.86 (~3.5% of price). Use this to scale stops, not fixed dollar amounts.
- **Trailing stop (longs):** Place a protective stop **~1.5× ATR (≈$10.3) below entry** or, structurally, **just below the 190 confluence (≈$188)**. A stop below 188 invalidates the "uptrend-intact" thesis.
- **Position sizing:** With volatility normalizing (8.55 → 6.86), you can carry a slightly larger position than during the June spike for the same risk budget. However, because the VWMA is still falling (unconfirmed bottom), **right-size to a half-position** on initial entry and add only on confirmation.
- **Invalidation signal:** A daily close **below $188** (under the 200 SMA + Bollinger LB) → stand aside; the golden-cross structure is at risk.

---

## 6. Actionable Insights & Trade Plan

1. **HOLD existing longs** — the long-term trend (rising 200 SMA, golden-cross spread) is intact. There is no technical basis to exit at $194.61.
2. **Do NOT chase** — price is below the 50 SMA and VWMA, MACD is negative, and RSI < 50. There is **no bullish confirmation yet**; buying here is catching a falling (if slowing) knife.
3. **Accumulation zone: ~190** — the 200 SMA / Bollinger LB confluence is the high-probability entry. A **small, half-size entry near 190** with a stop below 188 offers ~2:1 reward-to-risk toward the 201 VWMA / 209 50 SMA targets.
4. **Confirmation adds** — scale up only when **two** of the following occur: (a) RSI reclaims 50, (b) MACD histogram crosses above zero, (c) price reclaims the VWMA (~201) on rising volume.
5. **Watch the VWMA** — it is the laggard. If it flattens/rises alongside price, the correction is likely complete. If it keeps falling while price holds, expect a deeper, second-leg dip toward ~180.
6. **Beware the volatility squeeze** — ATR contraction (8.55 → 6.86) often precedes an expansion move. Expect the next directional resolution to be sharp; have the 188 stop pre-committed.

**Scenario probabilities (technical view):**
- **Base case (~55%):** Price consolidates in the 188–201 range, RSI recovers to 50+, histogram turns positive → trend resumes toward 209/220.
- **Bull case (~25%):** Strong reclaim of VWMA on volume → rapid retest of 209 (50 SMA), then 220+.
- **Bear case (~20%):** Break below 190/188 → deeper correction toward ~180, testing the 200 SMA's lower band before a base forms.

---

## 7. Summary Table

| Dimension | Indicator | Current Value | Reading | Signal |
|---|---|---|---|---|
| Long-term trend | 200 SMA | 190.71 (rising) | Price above, steady climb | 🟢 Bullish |
| Medium-term trend | 50 SMA | 209.28 | Price ~7% below; > 200 SMA | 🟡 Corrective |
| Momentum (level) | MACD | -4.09 | Negative since early June | 🔴 Bearish |
| Momentum (accel.) | MACD Hist. | -0.84 (from -2.65) | Rising toward zero | 🟡 Decelerating |
| Oscillator | RSI | 42.01 (from 37.57) | Recovering from oversold, < 50 | 🟡 Stabilizing |
| Volatility | ATR | 6.86 (from 8.55) | Contracting from June spike | 🟢 Risk normalizing |
| Support floor | Boll LB | 190.12 | Price ~4.5 pts above; 190 confluence | 🟡 Key support |
| Volume confirm. | VWMA | 201.00 (from 220.25) | Price below; still falling | 🔴 Unconfirmed |

**Composite:** 🟢 Long-term / 🟡 Medium-term / 🟡 Short-term stabilizing. The risk-reward is best at the **~190 support confluence**, not at the current $194.61.

---

FINAL TRANSACTION PROPOSAL: **HOLD**

*Rationale: Maintain long exposure — the 12-month uptrend remains structurally intact (price above rising 200 SMA, golden-cross spread preserved). However, do not add aggressively: the stock is in a corrective phase below the 50 SMA and VWMA, MACD is negative, and RSI is still under 50, so there is no bullish confirmation yet. The MACD histogram's recovery from its trough and RSI's rebound from near-oversold indicate downside momentum is exhausting, making the ~190 (200 SMA + Bollinger LB) confluence the high-probability accumulation zone. **HOLD core longs, scale into a half-position only near 190 with a stop below ~188, and add on confirmation** (RSI > 50, MACD histogram > 0, or VWMA reclaim on volume). A daily close below $188 invalidates the bullish structure and should trigger a defensive stance.*