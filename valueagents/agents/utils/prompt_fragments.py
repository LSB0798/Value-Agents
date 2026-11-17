"""统一的 LLM prompt 片段。

所有 analyst 共享同一份 Data Availability Protocol，
避免各文件不一致导致 LLM 误解。

三档判断（TOTAL / PARTIAL / FULL），防止 LLM 把"部分失败"误判为"全部失败"。
"""

DATA_AVAILABILITY_PROTOCOL = (
    "\n\n## Data Availability Protocol (MANDATORY)\n"
    "\n"
    "Tool results may start with one of these prefixes:\n"
    "- `[DATA_UNAVAILABLE]` — the tool has NO usable data for this request.\n"
    "- `[PARTIAL_DATA]` — the tool has SOME data but is incomplete.\n"
    "\n"
    "After ALL tool calls complete, apply the following decision tree:\n"
    "\n"
    "### A. TOTAL FAILURE\n"
    "Condition: you called one or more tools, and **EVERY** tool returned `[DATA_UNAVAILABLE]`.\n"
    "Action:\n"
    "  1. Write the EXACT marker `INSUFFICIENT_DATA: <short reason>` as the FIRST line of your report.\n"
    "  2. Keep the ENTIRE report under 200 words.\n"
    "  3. Briefly list what data is missing and why it matters.\n"
    "  4. STOP. Do NOT fabricate numbers, prices, dates, news headlines, analyst quotes, "
    "or hypothetical scenarios. Do NOT add Markdown tables. Do NOT write 'analysis' based on guesses.\n"
    "\n"
    "### B. PARTIAL FAILURE\n"
    "Condition: you called multiple tools, and **AT LEAST ONE** succeeded (no prefix) while "
    "**AT LEAST ONE** returned `[DATA_UNAVAILABLE]` or `[PARTIAL_DATA]`.\n"
    "Action:\n"
    "  1. Write a FULL report using the successful data (normal length and depth).\n"
    "  2. Do NOT start with `INSUFFICIENT_DATA`.\n"
    "  3. Add a short `## Data Gaps` section at the end listing what is missing.\n"
    "  4. Do NOT speculate about the missing data.\n"
    "\n"
    "### C. FULL SUCCESS\n"
    "Condition: all tools succeeded (no prefix).\n"
    "Action: write a normal full report. No `## Data Gaps` section needed.\n"
    "\n"
    "### Tool Usage Constraint\n"
    "You MUST call each tool at most ONCE. Do NOT call the same tool twice with different date ranges. "
    "Do NOT retry with a wider window.\n"
    "\n"
    "Violation of this protocol (writing speculative content when data is unavailable) "
    "will corrupt downstream analysis and is considered a critical error.\n"
)


__all__ = ["DATA_AVAILABILITY_PROTOCOL"]