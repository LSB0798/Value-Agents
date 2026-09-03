# valueagents/agents/researchers/bear_researcher.py

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pathlib import Path
from valueagents.agents.skills.loader import load_skill
from valueagents.agents.skills.loader import load_all_skills
import json
from langchain_core.messages import HumanMessage
from valueagents.agents.utils.compress_utils import compress_text
from valueagents.agents.utils.compress_utils import estimate_word_count


def create_bear_researcher(llm, memory):
    # --- 加载所有 Skills 作为工具 ---
    all_skills = load_all_skills()
    tools = all_skills

    print(f"[Bear Researcher] Loaded {len(tools)} tools: {[t.name for t in tools]}")

    # ====================================================================
    # Step 1: 提取 Bull 的核心主张
    # ====================================================================
    def step1_extract_bull_claims(bull_argument, llm):
        if not bull_argument or len(bull_argument.strip()) < 10:
            return "No clear bull argument provided yet. Proceed with general bear case."
        prompt = f"""
You are a Bear Analyst preparing for a debate.

Extract the 3-5 core claims from the Bull's argument.
Each claim should be a single sentence that captures the Bull's main point.

Bull's argument:
{bull_argument}

Output format (one claim per line, numbered):
1. [Claim 1]
2. [Claim 2]
3. [Claim 3]
"""
        return llm.invoke(prompt).content

    # ====================================================================
    # Step 2: Risks and Challenges（纯推理，不调用工具）
    # ====================================================================
    def step2_risks_and_challenges(bull_claims, market_report, news_report, llm):
        prompt = f"""
You are a Bear Analyst. Your task: Identify Risks and Challenges.

Bull's core claims: {bull_claims}

Available data:
Market report: {market_report}
Macro news: {news_report}

Instructions:
1. For each Bull claim, identify specific risks that undermine it.
2. Output a concise analysis (max 2 paragraphs) focusing on:
   - Market saturation risks
   - Financial instability risks
   - Macroeconomic threats
3. Use specific numbers from the data whenever possible.
"""
        return llm.invoke(prompt).content

    # ====================================================================
    # Step 3: Competitive Weaknesses（纯推理）
    # ====================================================================
    def step3_competitive_weaknesses(bull_claims, fundamentals_report, previous_conclusions, llm):
        prompt = f"""
You are a Bear Analyst. Your task: Identify Competitive Weaknesses.

Bull's core claims: {bull_claims}
Previous analysis: {previous_conclusions}

Available data:
Fundamentals report: {fundamentals_report}

Instructions:
1. Identify the company's competitive vulnerabilities.
2. Output a concise analysis (max 2 paragraphs) focusing on:
   - Weaker market positioning
   - Declining innovation or R&D efficiency
   - Competitive threats
3. Use specific metrics (ROE, margins, growth rates) from the data.
"""
        return llm.invoke(prompt).content

    # ====================================================================
    # Step 4: Negative Indicators（纯推理）
    # ====================================================================
    def step4_negative_indicators(bull_claims, sentiment_report, previous_conclusions, llm):
        prompt = f"""
You are a Bear Analyst. Your task: Identify Negative Indicators.

Bull's core claims: {bull_claims}
Previous analysis: {previous_conclusions}

Available data:
Sentiment report: {sentiment_report}

Instructions:
1. Find negative evidence (financial, market, or news) that contradicts Bull.
2. Output a concise analysis (max 2 paragraphs) focusing on:
   - Negative financial data trends
   - Bearish market signals
   - Adverse news sentiment
3. Use specific data points to support your claims.
"""
        return llm.invoke(prompt).content

    # ====================================================================
    # Step 5: Bull Counterpoints（生成反驳清单，纯推理）
    # ====================================================================
    def step5_bull_counterpoints(bull_claims, all_conclusions, past_memory_str, master_signals_text, llm):
        prompt = f"""
You are a Bear Analyst. Your task: Systematically rebut the Bull's argument.

Bull's core claims: {bull_claims}

Your analysis so far:
1. Risks & Challenges: {all_conclusions.get('step2', '')}
2. Competitive Weaknesses: {all_conclusions.get('step3', '')}
3. Negative Indicators: {all_conclusions.get('step4', '')}

Lessons from past mistakes (learn from these): {past_memory_str}

Master analyst signals (use these to strengthen your rebuttals): {master_signals_text}

Instructions:
1. For each Bull claim, provide a specific counterpoint using your analysis.
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
    def step6_tool_decision(bull_claims, counterpoints, llm, tools):
        if not tools:
            print("   ⚠️ Warning: No tools loaded. Tool decision will be skipped.")
        # 构建完整的工具描述列表（来自所有已加载的 Skills）
        tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
        
        prompt = f"""
You are a Bear Analyst. Review your counterpoints below and identify where you need data.

Bull's claims: {bull_claims}
Your counterpoints: {counterpoints}

Available tools (each is a specialized analyst skill):
{tool_descriptions}

Which tool(s) would provide data that strengthens your counterpoints?
- If NO tool is needed, output: "TOOL: none"
- If ONE tool is needed, output: "TOOL: tool_name"
- If MULTIPLE tools are needed, output: "TOOLS: tool_name1, tool_name2"

Output ONLY the tool selection, nothing else.
    """
        print('def step6_tool_decision tool_descriptions length : {}'.format(len(tool_descriptions))) # tool_descriptions length : 4827
        print('def step6_tool_decision bull_claims length : {}'.format(len(bull_claims))) # bull_claims length : 894
        print('def step6_tool_decision counterpoints length : {}'.format(len(counterpoints))) # counterpoints length : 3088
        print('def step6_tool_decision prompt length : {}'.format(len(prompt))) # prompt length : 9285
        return llm.invoke(prompt).content.strip()

    # ====================================================================
    # Step 7: 最终合成（融入工具结果，以 Engagement 风格输出）
    # ====================================================================
    def step7_final_synthesis(all_conclusions, bull_argument, past_memory_str, master_signals_text, tool_results, llm):
        tool_section = ""
        if tool_results:
            tool_section = "\nAdditional data from tools:\n"
            for name, result in tool_results.items():
                tool_section += f"\n--- {name} ---\n{result}\n"
        
        prompt = f"""
You are a Bear Analyst. Write the final bearish argument.

Your complete analysis:
{json.dumps(all_conclusions, indent=2)}

Bull's original argument for reference:
{bull_argument}

Master analyst signals (incorporate if relevant):
{master_signals_text}

Lessons from past mistakes (avoid repeating them):
{past_memory_str}
{tool_section}

Instructions:
1. Write a conversational, persuasive argument.
2. Start by directly engaging with the Bull's main point.
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
    # 主节点 bear_node（新版本）
    # ====================================================================
    def bear_node(state) -> dict:
        current_round = state["investment_debate_state"].get("count", 0) // 2 + 1
        print(f"\n{'='*60}")
        print(f"🐻 [BEAR RESEARCHER] Round {current_round}")

        # --- 提取状态数据 ---
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")
        current_response = investment_debate_state.get("current_response", "")

        # 👇 在这里插入 start_date 计算
        trade_date = state.get("trade_date")
        start_date = state.get("start_date")
        if not start_date and trade_date:
            from datetime import datetime, timedelta
            dt = datetime.strptime(trade_date, "%Y-%m-%d")
            start_date = (dt - timedelta(days=365)).strftime("%Y-%m-%d")

        # 报告（全量，按用户要求暂不压缩）
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
        print("   🔍 Step 1: Extracting Bull's core claims...")
        if not current_response or len(current_response.strip()) < 10:
            bull_claims = "No clear bull argument provided yet. Proceed with general bear case."
        else:
            print('step1_extract_bull_claims current_response : {}, length : {}'.format(current_response, len(current_response)))
            bull_claims = step1_extract_bull_claims(current_response, llm)
            # print('Step 1: bull_claims : {}'.format(bull_claims))
            print('Step 1: bull_claims length : {}'.format(len(bull_claims)))
        print(f"      → Claims extracted.")

        conclusions = {}

        print("   🔍 Step 2: Risks and Challenges...")
        conclusions["step2"] = step2_risks_and_challenges(bull_claims, market_report, news_report, llm)
        # print('Step 2: content : {}'.format(conclusions["step2"]))
        print('Step 2: content length : {}'.format(len(conclusions["step2"])))

        print("   🔍 Step 3: Competitive Weaknesses...")
        conclusions["step3"] = step3_competitive_weaknesses(bull_claims, fundamentals_report, conclusions["step2"], llm)
        # print('Step 3: content : {}'.format(conclusions["step3"]))
        print('Step 3: content length : {}'.format(len(conclusions["step3"])))

        print("   🔍 Step 4: Negative Indicators...")
        conclusions["step4"] = step4_negative_indicators(bull_claims, sentiment_report, conclusions["step2"], llm)
        # print('Step 4: content : {}'.format(conclusions["step4"]))
        print('Step 4: content length : {}'.format(len(conclusions["step4"])))

        print("   🔍 Step 5: Generating Bull Counterpoints...")
        conclusions["step5"] = step5_bull_counterpoints(bull_claims, conclusions, past_memory_str, master_signals_text, llm)
        # print('Step 5: content : {}'.format(conclusions["step5"]))
        print('Step 5: content length : {}'.format(len(conclusions["step5"])))

        # --- Step 6: 工具决策 ---
        print("   🔍 Step 6: Tool decision...")
        word_count_bull = estimate_word_count(bull_claims)
        compressed_bull_claims = compress_text(bull_claims, 
                                               max_words=max(60, int(word_count_bull * 0.5)), # max_words=len(bull_claims) * 0.5,
                                               role="bull claims summary")
        print('length of bull_claims : {}, compressed_bull_claims : {}'.format(len(bull_claims), len(compressed_bull_claims)))
        word_count_counter = estimate_word_count(conclusions["step5"])
        compressed_counterpoints = compress_text(conclusions["step5"], 
                                                 max_words=max(100, int(word_count_counter * 0.5)), # max_words=len(conclusions["step5"]) * 0.5,
                                                 role="bear counterpoints summary")
        print('length of conclusions["step5"] : {}, compressed_counterpoints : {}'.format(len(conclusions["step5"]), len(compressed_counterpoints)))
        tool_decision = step6_tool_decision(compressed_bull_claims, compressed_counterpoints, llm, tools)
        print(f"      → Tool decision: {tool_decision}")
        print(f"      → Tool decision length: {len(tool_decision)}")

        # 解析工具选择
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
        final_argument = step7_final_synthesis(conclusions, current_response, past_memory_str, master_signals_text, tool_results, llm)

        # ===== 补充：构造输出 =====
        argument = f"Bear Analyst: {final_argument}"
        print(f"   💬 Bear argument generated (length: {len(argument)} chars)")
        print(f"   Summary: {argument[:150].replace(chr(10), ' ')}...")

        final_message = HumanMessage(content=argument)
        new_messages = messages + [final_message]

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        print(f"[BEAR RESEARCHER] Round {current_round} complete.\n")
        print(f"{'='*60}")

        return {
            "messages": new_messages,
            "investment_debate_state": new_investment_debate_state,
            "bear_conclusions": conclusions,
            "bear_tool_decision": tool_decision,
        }

    return bear_node