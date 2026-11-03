<p align="center">
  <img src="assets/schema.png" style="width: 80%; height: auto;">
</p>

# TradingAgents with AI Hedge Fund Analysts

**TradingAgents** is a multi-agent trading decision framework that simulates a hedge fund investment team consisting of:

- **4 News Analysts** — multi-source news intelligence
- **19 Master Analysts** — inspired by legendary investors (Graham, Buffett, Munger, ...)
- **Bull / Bear Researchers** — adversarial debate with dynamic skill invocation
- **Research Manager** — synthesizes debate into an investment plan
- **Trader** — converts the plan into specific orders
- **3 Risk Analysts** (Aggressive / Neutral / Conservative) + **Portfolio Manager** — final decision

The system generates trading decisions through **multi-round debates**, **evidence-based skill selection**, and **comprehensive signal aggregation**.

## 🧠 Core Architecture

### Skill Layers

The system uses a **3-layer skill system**:

| Layer | Count | Examples | Runs Tool Loops? |
|---|---|---|---|
| **Core Skills** (`kind=leaf` / `kind=meta`) | 9 | `market_analyst`, `trader`, `research_team`, `risk_team` | ✅ (analysts only) |
| **Master Skills** (`kind=master`) | 19 | `warren_buffett_analyst`, `charlie_munger_analyst`, ... | ❌ (single LLM call) |
| **Orchestration Skills** (`orchestrators/`) | 1 meta | `master_team` | ❌ (delegates to masters) |

- **Core Skills** live in `agents/skills/core/` — each has `SKILL.md` (metadata) + `skill.py` (`execute(ctx) -> SkillResult`)
- **Master Skills** live in `agents/skills/{name}_skill/` — each has `SKILL.md` + `skill.py` (`execute(ticker, end_date, api_key) -> JSON`)
- **SkillCatalog** (`orchestrators/skill_catalog.py`) maintains `kind` / `requires` / `produces` for every skill, enabling `requires`-based precondition checks in chat mode

### Analyst Team

| Analyst Type | Count | Description |
|---|---|---|
| **Core Analysts** | 4 | `market` (technical, 8 indicators), `social` (news + sentiment), `news` (company + macro), `fundamentals` (statements). Each runs its own tool loop and produces one report. |
| **Master Analysts** | 19 | Based on investment philosophies of Graham, Buffett, Lynch, Munger, Burry, Wood, Damodaran, etc. Each performs quantitative analysis + LLM reasoning independently, outputs `bullish`/`bearish`/`neutral` with confidence. Exposes L1 metadata (`best_for` / `not_for` / `capabilities`) for on-demand selection. |

> **Master skill interface**:
> - All 19 master skills share the signature `execute(ticker, end_date, api_key) -> JSON` — **except `technical_analyst`, which requires an additional `start_date`** (defaults to `end_date - 365d` when invoked via `master_team` / `hf_analysts_wrapper`)
> - Master names in `SkillCatalog` and `select_master_analysts()` carry the `_analyst` suffix (e.g. `warren_buffett_analyst`), but `hf_analysts_wrapper` accepts both `warren_buffett` and `warren_buffett_analyst`
> - `technical_analyst` and `news_sentiment_analyst` are also exposed in the master list even though they are technically composite agents
> 💡 **Progressive Disclosure**: Master skills are loaded once into a singleton `SkillRegistry`. Bull/Bear Researchers query the L1 view (name + 120-char description + `best_for`/`not_for`/`capabilities`) to select candidates, then invoke selected skills via the registry. Only the selected skill's `## Workflow` is injected into its internal LLM prompt — keeping the debate prompt lightweight.

### Workflow

#### Graph Mode (fixed pipeline)

The default LangGraph pipeline is **serial** (analysts run one at a time, not in parallel):

1. **4 Core Analysts** (serial): `market_analyst` → `social_analyst` → `news_analyst` → `fundamentals_analyst`. Each runs its own tool loop and produces one report.
2. **Research Team** (`research_team` meta skill): internal Bull↔Bear multi-round debate.
   - Debate depth is **configurable** (1 / 3 / 5 rounds = shallow / medium / deep).
   - At each round, each researcher **autonomously selects skills** (from the 19 master skills) to fill argument gaps, guided by L1 metadata. Skills already invoked in prior rounds are excluded.
   - Selected skills run sequentially inside the researcher's step loop.
   - After the final round, the **Research Manager** synthesizes the debate into `investment_plan`.
3. **Trader**: converts `investment_plan` into a specific trade plan.
4. **Risk Team** (`risk_team` meta skill): 3-way risk debate (Aggressive / Conservative / Neutral), 1–5 rounds. History is compressed every 2 rounds to keep the prompt bounded.
5. **Portfolio Manager**: synthesizes all information → `final_trade_decision` (`BUY`/`SELL`/`HOLD`/`OVERWEIGHT`/`UNDERWEIGHT`).

#### Chat Mode (conversational)

`python cli/main.py --mode chat` starts a REPL where an LLM orchestrator picks skills on-demand:

1. **Setup**: user selects ticker / date / language / research depth / **master analysts to run** (optional, default 3).
2. **Conversation**: user types natural-language requests like `完整分析 GOOGL`, `用三个大师分析一下`, `只跑 market_analyst`.
3. **Orchestrator loop**: each step the LLM outputs `{"action": "call", "skill": "..."}` or `{"action": "done", "answer": "..."}`.
   - Before calling a skill, `requires` is validated against current artifacts — missing preconditions cause a rejection message (not a crash).
   - Artifacts accumulate across steps: `market_report` → `sentiment_report` → ... → `final_trade_decision`.
4. **Full-analysis pipeline** (when user says "完整分析"): the orchestrator follows the canonical pipeline documented in `prompts.py → ## Full Analysis Pipeline`:
   - 4 core analysts → **master_team** (if any masters configured; skipped if none) → research_team → trader → risk_team → portfolio_manager
   - `master_team` is included only when it appears in the rendered skill list; if the user configured zero masters, the orchestrator skips step 5
   - The LLM is instructed NOT to skip `master_team` when the user says "完整分析" and masters are available

#### Master Team (batch invocation)

`master_team` skill runs N user-selected master analysts in one shot:
- **Input**: `requires` the 4 core reports.
- **Process**: **prefetch shared data → run selected masters** (currently sequential; parallel execution is a future optimization).
- **Output**: `master_analyst_signals` (`{master_name: {signal, confidence, reasoning}}`) + `master_summary`.

### Data Sources

- **Financial Data**: Retrieved from **yfinance** and **SEC EDGAR** (free, no API key required). The legacy Financial Datasets API is only used as a fallback when both free sources are disabled.
  - **yfinance** — current market data, price history, and quarterly/annual financials.
  - **SEC EDGAR** — authoritative annual filings (10-K) for long-term fundamental analysis.
  - **ROIC API** — quarterly fundamentals for TTM (trailing-twelve-month) calculation.
  - **Finnhub** — insider trades.
  - **Alpha Vantage** — news with built-in sentiment.

### Data Caching

To reduce API calls and speed up repeated analyses, the system **persists data locally** in `dataflows/data_cache/`.  
All data is stored by type and ticker, and new data is merged with existing cached data (deduplicated by date/key), so you won't lose historical data when running new analyses.

The cache directory structure is as follows:

```text
dataflows/data_cache/
├── line_items/                 # Detailed line items (JSON per ticker+period)
│   └── AAPL_ttm_line_items.json
├── insider/                    # Insider trades (JSON per ticker)
│   └── AAPL_insider.json
├── news/                       # Company news (JSON per ticker)
│   ├── AAPL_news.json
│   └── GLOBAL_news.json
└── market_cap/                 # Per (ticker, date) market cap
    └── AAPL_2026-09-10.json
```

- **Prices**: CSV files, one per ticker, containing all daily price data (date range as filename).
- **Fundamentals**: JSON files storing quarterly/annual financial metrics and raw statements.
- **Line Items**: JSON files for detailed financial line items (e.g., revenue, debt, cash flow).
- **Insider**: JSON files for insider transaction history.
- **News**: JSON files for company news (from Alpha Vantage, Finnhub, etc.).

> **Note**: The cache is automatically managed. If you ever need to reset it, simply delete the `dataflows/data_cache/` directory or individual files. The system will rebuild them on the next run.

### Known Limitations

- **`news_sentiment_analyst` returns `confidence=0.0`** in some runs — the internal per-article LLM classification occasionally fails to parse headlines; under investigation (fallback returns `neutral`/`0.0` rather than crashing)
- **`master_team` runs masters sequentially** — parallel execution is planned for a future release. Current 19-master runs take 20–30 min; `prefetch_shared_data()` already minimizes data-source requests so the bottleneck is pure LLM latency
- **Graph mode vs chat mode may produce different decisions** for the same ticker/date — LLM non-determinism plus different debate-round counts (graph defaults to `min=3, max=8`; chat uses `research_depth`) can flip a marginal case. Not a bug, but worth noting for A/B comparisons
- **Reflection loop is wired but not triggered** — `FinancialSituationMemory` is injected into state and read by Bull/Bear `get_memories()`, but `reflect_and_remember()` is never called because the `returns_losses` source (future price → realized return) is not yet implemented. Memory is effectively empty until a reflection script populates it
- **`news_analyst` global feed can be empty** — the aggregator returns "insufficient data" when GNews / Finnhub / AlphaVantage are all rate-limited or offline; the analyst is instructed to write "insufficient data" rather than retry

### Data Correctness (end_date filtering)

All `get_financial_metrics` / `search_line_items` calls are **filtered by `end_date`** to avoid look-ahead bias:
- `report_period > end_date` rows are dropped before returning to any skill.
- `_filter_by_report_period` (in `api.py`) applies the filter to every metrics list.
- `_filter_years_by_end_date` keeps a fiscal year only if `f"{year}-12-31" <= end_date`. This is conservative: for companies with non-Dec fiscal year-ends (e.g. NVDA ending Jan 31, AAPL ending Sep 30), the current year's already-reported data may be filtered out if `Dec 31 > end_date`. This trades "never leak future data" for "occasionally missing the most recent fiscal year". A future release could use the vendor-reported `report_period` instead of the hard-coded Dec 31.
- Cache reads are also filtered, so stale future-dated data never reaches an analyst.

### Prefetch (data source optimization)

Before `master_team` / `research_team` execute, `prefetch_shared_data(ticker, end_date)` serially warms the cache for **8 logical data sources**:

| # | Data source | Cache keys written | Notes |
|---|---|---|---|
| 1 | `financial_metrics` (ttm) | limits `5, 8, 10, 12` | One fetch at `limit=12`, sliced into 4 keys |
| 2 | `financial_metrics` (annual) | limits `5, 10` | One fetch at `limit=10`, sliced into 2 keys |
| 3 | `line_items` (ttm) | all `_ALL_LINE_ITEM_FIELDS` | Full field set |
| 4 | `line_items` (annual) | all `_ALL_LINE_ITEM_FIELDS` | Full field set |
| 5 | `prices` | `end_date-365 → end_date` | Matches `technical_analyst` / `nassim_taleb` |
| 6 | `insider_trades` | `end_date-365 → end_date` | Matches `charlie_munger` / `sentiment` / others |
| 7 | `company_news` + aggregated news | 30-day + 7-day windows | Covers `news_sentiment` + `phil_fisher` / `lynch` etc. |
| 8 | `market_cap` | `(ticker, end_date)` | Shared by all masters |

**Design properties**:
- **Idempotent within a process** — `_prefetch_done` set prevents re-running for the same `(ticker, end_date)`; safe to call from `master_team.execute()` and `research_team.execute()` even if both run in the same session
- **Per-source isolation** — each data source is wrapped in `try/except`; a single failure logs a warning but does not abort the others
- **Exact cache key coverage** — because `get_financial_metrics` / `search_line_items` include `limit` in the cache key, prefetch fetches max limit once and writes all possible limit variants; without this, each master with a different `limit` would trigger a separate upstream request

**Effect**: 19 master skills + Bull/Bear's ~26 skill calls share the same cached data. Data-source API requests drop from ~70–110 to ~6–8 per full analysis. Cache key lookup uses `(ticker, period, end_date, limit)` — prefetch writes all possible limits so any master skill's cache lookup hits.

### Context Compressor (4-layer)

To keep prompts bounded and avoid API rate limits, each analyst has a 4-layer compression pipeline:
- **L1**: rule gates (invalid data / short text / oversized offload)
- **L2**: threshold check (only compress when cumulative `consumed_tokens` exceeds 80% of budget)
- **L3**: two-stage LLM compression (extract → summarize), with `query_reason` + recent summaries as context
- **L4**: circuit breaker (3 consecutive failures → local truncate) + budget-exhausted fast path

Budget-exhausted fast path: when `consumed_tokens >= token_budget`, `compress()` skips L3 and calls `safe_truncate` directly — avoiding repeated 20-second LLM calls at end-of-analysis.

### Optional Feature: RAG (Retrieval‑Augmented Generation)

RAG is disabled by default but can be enabled optionally. When activated, agents can query a local knowledge base (e.g., Buffett’s letters, Munger’s speeches) to enhance their reasoning. For setup details, see the RAG Service Setup section below.

### Skills System (Extension Point)

Skills are modular, plug-and-play packages. There are two kinds:

#### Master Skills (`agents/skills/{name}_skill/`)
- `SKILL.md` — YAML frontmatter (`name`, `description`, `best_for`, `not_for`, `capabilities`, `inputs`) + `## Workflow` section
- `skill.py` — exports `execute(ticker, end_date, api_key) -> json_str`

#### Core Skills (`agents/skills/core/{name}_skill/`)
- Same structure, but `execute(ctx: SkillContext) -> SkillResult`
- `ctx.artifacts` holds upstream reports (from `ArtifactStore` in chat mode, or LangGraph state in graph mode)
- `ctx.config` holds runtime config (`max_debate_rounds`, `master_analysts`, etc.)

#### Skill Registry & Catalog
- `SkillRegistry` — singleton, loads all master skills once at startup
- `SkillCatalog` — hard-codes `kind` / `requires` / `produces` for the 9 core skills and exposes `all_skills()` for prompt rendering
- `SkillAdapter` (`orchestrators/skill_adapter.py`) — unified invoke for both kinds; handles contextvars LLM injection

```text
agents/skills/
├── buffett_skill/          # master (19 total)
│   ├── SKILL.md
│   └── skill.py
├── munger_skill/
├── ...
└── core/                   # core (9 total)
    ├── market_analyst_skill/
    ├── social_analyst_skill/
    ├── news_analyst_skill/
    ├── fundamentals_analyst_skill/
    ├── trader_skill/
    ├── research_manager_skill/
    ├── portfolio_manager_skill/
    ├── risk_team_skill/
    └── research_team_skill/
```

## 🧪 What's New

### v0.2.1 — Master Skill Interface Fixes + Prefetch Refinement

- **Master name normalization** — `hf_analysts_wrapper._normalize_master_name` now accepts both `warren_buffett` and `warren_buffett_analyst`; `get_master_analyst_node` produces consistent `agent_id` (`{normalized}_agent`) regardless of input form
- **`technical_analyst` special case** — `master_team` and `hf_analysts_wrapper` now pass `start_date = end_date - 365d` only for `technical_analyst` (the other 18 masters use `(ticker, end_date, api_key)`); previously this raised `TypeError: execute() missing 1 required positional argument: 'start_date'`
- **`skill_adapter._invoke_core` config pass-through** — `ctx.config` now includes `master_analysts`; previously it was dropped, causing `master_team` to always use the default 3 masters instead of the user's selection
- **`aswath_damodaran` `{year10}` escaping** — the `## Workflow` section contained `FCFF_{year10}`, which `ChatPromptTemplate` treated as a variable and raised `KeyError: 'year10'` → `confidence=0.0`. Fixed at the source: `loader._extract_workflow` now escapes all `{`/`}` so workflow text is treated as literal
- **Full-analysis pipeline prompt** — `prompts.py` now includes an explicit `## Full Analysis Pipeline` section (4 analysts → master_team → research_team → trader → risk_team → portfolio_manager). Without it, the LLM skipped `master_team` for "完整分析" requests
- **Compression budget fast path** — `compress()` now short-circuits to `safe_truncate` when `consumed_tokens >= token_budget` (avoids 3-5 wasted 20-second L3 calls per analyst in 19-master runs)

### v0.2.2 — Skill-ified Pipeline + Conversational Mode

- **9 core skills** extracted from LangGraph nodes (`market_analyst` / `social_analyst` / `news_analyst` / `fundamentals_analyst` / `trader` / `research_manager` / `portfolio_manager` / `risk_team` / `research_team`)
- **Chat mode** via `ConversationalOrchestrator` with `requires`/`produces` precondition checks
- **`master_team` skill** — run N selected masters in one step (currently sequential, parallel TBD)
- **LLM callbacks fixed** via `contextvars` — 19 master skills now inherit the main LLM's `StatsCallbackHandler`. In representative runs the observed LLM call count roughly doubles (101 → 161 for a full analysis, and every master-skill invocation is now counted), because previously each master skill rebuilt its own LLM client via `get_model()` and dropped the callback handler.
- **Risk debate history compression** — `risk_team` history compressed to ≤ 18K chars every 2 rounds (was 196K → now ~50K)
- **`used_skills` isolation** — Bull and Bear researchers now maintain independent `used_skills` pools (previously shared, causing Bear to run out of skills in later rounds)
- **`end_date` filtering** — all metrics/line-items filtered to `report_period <= end_date` to eliminate look-ahead bias
- **Prefetch** — `master_team` / `research_team` warm the cache for 8 data sources before execution (API requests drop from ~70–110 to ~6–8)
- **Compression budget fast path** — `compress()` skips L3 when `consumed_tokens >= token_budget` (avoided repeated 20-second LLM calls in 19-master runs)
- **Memory injection** — 5 `FinancialSituationMemory` instances are now injected into LangGraph state for reflection (link is connected; reflection loop TBD)
- **`_SKILL.md` YAML workflow escaping** — all `## Workflow` sections are now `{`-escaped to prevent `ChatPromptTemplate` from treating them as template variables

### v0.1 — Initial release
- 19 master analysts as skills
- Bull/Bear debate with dynamic skill invocation
- Risk debate (Aggressive / Conservative / Neutral)
- Portfolio manager final decision

## 📦 Installation & Usage

### Requirements

- Python 3.13+
- Docker (optional but recommended)

### Clone & Install

```bash
git clone https://github.com/LSB0798/Value-Agents.git
cd Value-Agents
conda create -n valueagents python=3.10
conda activate valueagents
pip install .
```

# Required for financial data
## Data source toggles (recommended: enable both free sources)
USE_YFINANCE=true          # Use yfinance for prices, metrics, quarterly data
USE_EDGAR=true             # Use SEC EDGAR for authoritative annual filings

## Legacy: only needed if you disable both free sources above
FINANCIAL_DATASETS_API_KEY=your-api-key

## News API keys (optional — only required if you use the corresponding analyst)
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
FINNHUB_API_KEY=your-finnhub-key
GNEWS_API_KEY=your-gnews-key

## For LLM (OpenAI-compatible local endpoint)
OPENAI_API_BASE=http://your-local-llm:port/v1
OPENAI_API_KEY=dummy

# News API keys (optional — only required if you use the corresponding analyst)
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
FINNHUB_API_KEY=your-finnhub-key
GNEWS_API_KEY=your-gnews-key

# For LLM (OpenAI‑compatible local endpoint)
OPENAI_API_BASE=http://your-local-llm:port/v1
OPENAI_API_KEY=dummy

# Run
```
# Run — Graph mode (fixed 5-stage pipeline)
python cli/main.py
```

```
# Run — Chat mode (conversational)
python cli/main.py --mode chat

# Chat mode REPL commands:
#   :help              show help
#   :config            show current config
#   :new               switch ticker / date
#   exit               quit

# Chat mode examples:
#   你 > 完整分析 GOOGL
#   你 > 用三个大师分析一下
#   你 > 只跑 market_analyst
#   你 > 直接给我 research decision     (will be rejected — missing preconditions)
```


