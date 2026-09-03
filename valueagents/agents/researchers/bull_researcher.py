# valueagents/agents/researchers/bull_researcher.py

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pathlib import Path
from langchain_core.messages import HumanMessage
import json
from valueagents.agents.skills.loader import load_all_skills
from valueagents.agents.utils.compress_utils import compress_text, estimate_word_count


def create_bull_researcher(llm, memory):
    # --- 加载所有 Skills 作为工具 ---
    all_skills = load_all_skills()
    tools = all_skills

    print(f"[Bull Researcher] Loaded {len(tools)} tools: {[t.name for t in tools]}")

    # ====================================================================
    # Step 1: 提取 Bear 的核心主张
    # ====================================================================
    def step1_extract_bear_claims(bear_argument, llm):
        if not bear_argument or len(bear_argument.strip()) < 10:
            return "No clear bear argument provided yet. Proceed with general bull case."
        prompt = f"""
You are a Bull Analyst preparing for a debate.

Extract the 3-5 core claims from the Bear's argument.
Each claim should be a single sentence that captures the Bear's main point.

Bear's argument:
{bear_argument}

Output format (one claim per line, numbered):
1. [Claim 1]
2. [Claim 2]
3. [Claim 3]
"""
        return llm.invoke(prompt).content

    # ====================================================================
    # Step 2: 分析增长潜力（纯推理）
    # ====================================================================
    def step2_growth_potential(bear_claims, market_report, news_report, llm):
        prompt = f"""
You are a Bull Analyst. Your task: Identify Growth Potential.

Bear's core claims: {bear_claims}

Available data:
Market report: {market_report}
Macro news: {news_report}

Instructions:
1. For each Bear claim, highlight growth drivers that counter it.
2. Output a concise analysis (max 2 paragraphs) focusing on:
   - Market opportunities and expansion potential
   - Revenue growth drivers
   - Scalability and new product pipelines
3. Use specific numbers from the data whenever possible.
"""
        return llm.invoke(prompt).content

    # ====================================================================
    # Step 3: 分析竞争优势（纯推理）
    # ====================================================================
    def step3_competitive_advantages(bear_claims, fundamentals_report, previous_conclusions, llm):
        prompt = f"""
You are a Bull Analyst. Your task: Identify Competitive Advantages.

Bear's core claims: {bear_claims}
Previous analysis: {previous_conclusions}

Available data:
Fundamentals report: {fundamentals_report}

Instructions:
1. Identify the company's competitive strengths.
2. Output a concise analysis (max 2 paragraphs) focusing on:
   - Unique products or services
   - Strong branding or market positioning
   - Technological or operational advantages
3. Use specific metrics (ROE, margins, market share) from the data.
"""
        return llm.invoke(prompt).content

    # ====================================================================
    # Step 4: 分析积极指标（纯推理）
    # ====================================================================
    def step4_positive_indicators(bear_claims, sentiment_report, previous_conclusions, llm):
        prompt = f"""
You are a Bull Analyst. Your task: Identify Positive Indicators.

Bear's core claims: {bear_claims}
Previous analysis: {previous_conclusions}

Available data:
Sentiment report: {sentiment_report}

Instructions:
1. Find positive evidence (financial, market, or news) that contradicts Bear.
2. Output a concise analysis (max 2 paragraphs) focusing on:
   - Positive financial trends
   - Bullish market signals
   - Favorable news sentiment
3. Use specific data points to support your claims.
"""
        return llm.invoke(prompt).content

    # ====================================================================
    # Step 5: Bull Counterpoints（生成反驳清单，纯推理）
    # ====================================================================
    def step5_bull_counterpoints(bear_claims, all_conclusions, past_memory_str, master_signals_text, llm):
        prompt = f"""
You are a Bull Analyst. Your task: Systematically rebut the Bear's argument.

Bear's core claims: {bear_claims}

Your analysis so far:
1. Growth Potential: {all_conclusions.get('step2', '')}
2. Competitive Advantages: {all_conclusions.get('step3', '')}
3. Positive Indicators: {all_conclusions.get('step4', '')}

Lessons from past mistakes (learn from these): {past_memory_str}

Master analyst signals (use these to strengthen your rebuttals): {master_signals_text}

Instructions:
1. For each Bear claim, provide a specific counterpoint using your analysis.
2. Use exact data references where possible.
3. Output as bullet points that directly refute each claim.

Format:
- Claim 1: [Your counterpoint with evidence]
- Claim 2: [Your counterpoint with evidence]
"""
        return llm.invoke(prompt).content

    # ====================================================================
    # Step 6: 工具决策节点（审查数据缺口，决定是否调用工具）
    # ====================================================================
    def step6_tool_decision(bear_claims, counterpoints, llm, tools):
        if not tools:
            print("   ⚠️ Warning: No tools loaded. Tool decision will be skipped.")
        # 构建完整的工具描述列表
        tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
        
        prompt = f"""
You are a Bull Analyst. Review your counterpoints below and identify where you need data.

Bear's claims: {bear_claims}
Your counterpoints: {counterpoints}

Available tools (each is a specialized analyst skill):
{tool_descriptions}

Which tool(s) would provide data that strengthens your counterpoints?
- If NO tool is needed, output: "TOOL: none"
- If ONE tool is needed, output: "TOOL: tool_name"
- If MULTIPLE tools are needed, output: "TOOLS: tool_name1, tool_name2"

Output ONLY the tool selection, nothing else.
    """
        print('def step6_tool_decision tool_descriptions length : {}'.format(len(tool_descriptions)))
        print('def step6_tool_decision bear_claims length : {}'.format(len(bear_claims)))
        print('def step6_tool_decision counterpoints length : {}'.format(len(counterpoints)))
        print('def step6_tool_decision prompt length : {}'.format(len(prompt)))
        return llm.invoke(prompt).content.strip()

    # ====================================================================
    # Step 7: 最终合成（融入工具结果，以 Engagement 风格输出）
    # ====================================================================
    def step7_final_synthesis(all_conclusions, bear_argument, past_memory_str, master_signals_text, tool_results, llm):
        tool_section = ""
        if tool_results:
            tool_section = "\nAdditional data from tools:\n"
            for name, result in tool_results.items():
                tool_section += f"\n--- {name} ---\n{result}\n"
        
        prompt = f"""
You are a Bull Analyst. Write the final bullish argument.

Your complete analysis:
{json.dumps(all_conclusions, indent=2)}

Bear's original argument for reference:
{bear_argument}

Master analyst signals (incorporate if relevant):
{master_signals_text}

Lessons from past mistakes (avoid repeating them):
{past_memory_str}
{tool_section}

Instructions:
1. Write a conversational, persuasive argument.
2. Start by directly engaging with the Bear's main point.
3. Present your strongest evidence first.
4. Use a confident, analytical tone.
5. End with a clear conclusion.
6. Maximum 500 words.

Output only the argument, no formatting.
"""
        return llm.invoke(prompt).content

    # ====================================================================
    # 辅助：精简大师信号
    # ====================================================================
    def format_master_signals(master_signals):
        if not master_signals:
            return "No additional master analyst signals available."
        lines = []
        for analyst_name, signals in master_signals.items():
            for ticker, sig in signals.items():
                lines.append(f"- {analyst_name}: {sig.get('signal', 'neutral')} ({sig.get('confidence', 0)}%)")
        result = "\n".join(lines[:10])
        return result if result else "No master signals available."

    # ====================================================================
    # 主节点 bull_node（重构版）
    # ====================================================================
    def bull_node(state) -> dict:
        current_round = state["investment_debate_state"].get("count", 0) // 2 + 1
        print(f"\n{'='*60}")
        print(f"🐂 [BULL RESEARCHER] Round {current_round}")

        # --- 提取状态数据 ---
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")
        current_response = investment_debate_state.get("current_response", "")

        # 计算 start_date（为 technical_analyst 准备）
        trade_date = state.get("trade_date")
        start_date = state.get("start_date")
        if not start_date and trade_date:
            from datetime import datetime, timedelta
            dt = datetime.strptime(trade_date, "%Y-%m-%d")
            start_date = (dt - timedelta(days=365)).strftime("%Y-%m-%d")

        # 报告（全量，暂不压缩）
        market_report = state.get("market_report", "")
        sentiment_report = state.get("sentiment_report", "")
        news_report = state.get("news_report", "")
        fundamentals_report = state.get("fundamentals_report", "")

        # 过往记忆
        curr_situation = f"{market_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)
        past_memory_str = "\n\n".join([rec["recommendation"] for rec in past_memories]) if past_memories else ""

        # Master signals（精简）
        master_signals = state.get("master_analyst_signals", {})
        master_signals_text = format_master_signals(master_signals)

        # 消息历史（纯净，只保留最终结果）
        messages = list(state.get("messages", []))

        # --- 执行步骤 1-5（纯推理） ---
        print("   🔍 Step 1: Extracting Bear's core claims...")
        print('   🔍 Step 1: current_response : {}'.format(current_response))
        if not current_response or len(current_response.strip()) < 10:
            bear_claims = "No clear bear argument provided yet. Proceed with general bull case."
        else:
            print('-0-' * 10)
            print('step1_extract_bear_claims current_response : {}'.format(current_response))
            bear_claims = step1_extract_bear_claims(current_response, llm)
            print('-1-' * 10)
            print('Step 1: bull_claims : {}'.format(bear_claims))
            print('Step 1: bear_claims length : {}'.format(len(bear_claims)))
        print(f"      → Claims extracted.")

        conclusions = {}

        print("   🔍 Step 2: Growth Potential...")
        conclusions["step2"] = step2_growth_potential(bear_claims, market_report, news_report, llm)
        print('Step 2: content : {}'.format(conclusions["step2"]))
        print('Step 2: content length : {}'.format(len(conclusions["step2"])))

        print("   🔍 Step 3: Competitive Advantages...")
        conclusions["step3"] = step3_competitive_advantages(bear_claims, fundamentals_report, conclusions["step2"], llm)
        print('Step 3: content : {}'.format(conclusions["step3"]))
        print('Step 3: content length : {}'.format(len(conclusions["step3"])))

        print("   🔍 Step 4: Positive Indicators...")
        conclusions["step4"] = step4_positive_indicators(bear_claims, sentiment_report, conclusions["step2"], llm)
        print('Step 4: content : {}'.format(conclusions["step4"]))
        print('Step 4: content length : {}'.format(len(conclusions["step4"])))

        print("   🔍 Step 5: Generating Bull Counterpoints...")
        conclusions["step5"] = step5_bull_counterpoints(bear_claims, conclusions, past_memory_str, master_signals_text, llm)
        # print('Step 5: content : {}'.format(conclusions["step5"]))
        # print('Step 5: content length : {}'.format(len(conclusions["step5"])))

        # --- Step 5.6: 压缩 bull_claims 和 counterpoints（用于工具决策） ---
        word_count_bear = estimate_word_count(bear_claims)
        compressed_bear_claims = compress_text(
            bear_claims,
            max_words=max(60, int(word_count_bear * 0.5)),
            role="bear claims summary"
        )
        print('   [Compressed] bear_claims: {}, bear_claims: {} chars'.format(bear_claims, compressed_bear_claims))
        print('   [Compressed] bear_claims: {} → {} chars'.format(len(bear_claims), len(compressed_bear_claims)))
        word_count_counter = estimate_word_count(conclusions["step5"])
        compressed_counterpoints = compress_text(
            conclusions["step5"],
            max_words=max(100, int(word_count_counter * 0.5)),
            role="bull counterpoints summary"
        )
        # print('   [Compressed] counterpoints: {} → {} chars'.format(len(conclusions["step5"]), len(compressed_counterpoints)))

        # --- Step 6: 工具决策 ---
        print("   🔍 Step 6: Tool decision...")
        print('length of conclusions["step5"] : {}, compressed_counterpoints : {}'.format(len(conclusions["step5"]), len(compressed_counterpoints)))
        tool_decision = step6_tool_decision(compressed_bear_claims, compressed_counterpoints, llm, tools)
        print(f"      → Tool decision: {tool_decision}")
        print(f"      → Tool decision length: {len(tool_decision)}")

        # 解析工具选择（兼容大小写）
        tool_decision_lower = tool_decision.lower()
        tool_names = []

        if "none" in tool_decision_lower:
            pass
        elif "tools:" in tool_decision_lower:
            parts = tool_decision.split(":", 1)
            if len(parts) == 2:
                tool_names = [name.strip() for name in parts[1].split(",")]
        elif "tool:" in tool_decision_lower:
            parts = tool_decision.split(":", 1)
            if len(parts) == 2:
                tool_names = [parts[1].strip()]
        else:
            print(f"      ⚠️ Unrecognized tool decision format: {tool_decision}")

        print(f"      → Selected tools: {tool_names if tool_names else 'none'}")

        # 执行所有选中的工具
        tool_results = {}
        for tool_name in tool_names:
            tool_obj = next((t for t in tools if t.name == tool_name), None)
            if tool_obj:
                try:
                    print(f"      → Calling {tool_name}...")
                    params = {"ticker": state["company_of_interest"], "end_date": state.get("trade_date")}
                    if tool_name == "technical_analyst" and start_date:
                        params["start_date"] = start_date
                    result = tool_obj.func(**params)
                    tool_results[tool_name] = result
                except Exception as e:
                    print(f"      ⚠️ Error calling {tool_name}: {e}")
                    tool_results[tool_name] = f"[Error: {e}]"
            else:
                print(f"      ⚠️ Tool '{tool_name}' not found in loaded tools. Skipping.")

        # --- Step 7: 最终合成 ---
        print("   🔍 Step 7: Synthesizing final argument...")
        final_argument = step7_final_synthesis(
            conclusions, current_response, past_memory_str,
            master_signals_text, tool_results, llm
        )

        # ===== 构造输出 =====
        argument = f"Bull Analyst: {final_argument}"
        print(f"   💬 Bull argument generated (length: {len(argument)} chars)")
        print(f"   Summary: {argument[:150].replace(chr(10), ' ')}...")

        final_message = HumanMessage(content=argument)
        new_messages = messages + [final_message]

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        print(f"[BULL RESEARCHER] Round {current_round} complete.\n")
        print(f"{'='*60}")

        return {
            "messages": new_messages,
            "investment_debate_state": new_investment_debate_state,
            "bull_conclusions": conclusions,
            "bull_tool_decision": tool_decision,
        }

    return bull_node