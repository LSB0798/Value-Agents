# valueagents/agents/researchers/bear_researcher.py

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pathlib import Path
from valueagents.agents.skills.loader import load_skill
from valueagents.agents.skills.loader import load_all_skills

# added prints for master_signals

def create_bear_researcher(llm, memory):
    # --- 加载所有 Skills 作为工具 ---
    all_skills = load_all_skills()
    tools = all_skills

    print(f"[Bear Researcher] Loaded {len(tools)} tools: {[t.name for t in tools]}")

    def bear_node(state) -> dict:
        # ========== 1. 节点入口打印 ==========
        current_round = state["investment_debate_state"].get("count", 0) // 2 + 1
        print(f"\n{'='*60}")
        print(f"🐻 [BEAR RESEARCHER] Round {current_round}")
        # print(f"{'='*60}")

        #############################################################################
        ################################### added prints ###################################
        print("\n🐻 BEAR RESEARCHER: Starting debate round...") #################### added prints
    
        master_signals = state.get("master_analyst_signals", {})
        if master_signals:
            print("   📚 Using master analyst signals:")
            for agent, signals in master_signals.items():
                for ticker, sig in signals.items():
                    print(f"      - {agent}: {ticker} -> {sig.get('signal')} (conf: {sig.get('confidence')})")
        else:
            print("   ⚠️ No master analyst signals available.")
        ################################### added prints ###################################
        #############################################################################

        # ========== 3. 提取状态数据（原有代码） ==========
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")
        current_response = investment_debate_state.get("current_response", "")

        # ========== 2. 打印对方（多头）的论点 ==========
        if current_response:
            content = current_response.replace("Bull Analyst:", "").strip()
            print(f"   📩 Received Bull argument: {content[:150].replace(chr(10), ' ')}...")
        else:
            print("   📩 No previous argument (starting debate)")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)
        past_memory_str = "\n\n".join([rec["recommendation"] for rec in past_memories])
        # past_memory_str = ""
        # for i, rec in enumerate(past_memories, 1):
        #     past_memory_str += rec["recommendation"] + "\n\n"

        # ========================================== master_analyst_signals 注入到 prompts ========================================== #
        # 格式化大师信号
        master_signals = state.get("master_analyst_signals", {})
        master_signals_text = ""
        if master_signals:
            master_signals_text = "\n\nAdditional insights from investment masters:\n"
            for analyst_name, signals in master_signals.items():
                for ticker, sig in signals.items():
                    master_signals_text += f"- {analyst_name.replace('_', ' ').title()} on {ticker}: {sig.get('signal', 'neutral').upper()} (confidence {sig.get('confidence', 0)}%)\n"
                    if 'reasoning' in sig:
                        master_signals_text += f"  Reasoning: {sig['reasoning']}\n"
        else:
            master_signals_text = "\n\nNo additional master analyst signals available.\n"
        # master_signals_text length : 11338
        # ========================================== master_analyst_signals 注入到 prompts ========================================== #

        tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])

        system_message_v1 = f"""You are a Bear Analyst making the case against investing in the stock. Your goal is to present a well-reasoned argument emphasizing risks, challenges, and negative indicators. Leverage the provided research and data to highlight potential downsides and counter bullish arguments effectively.

Key points to focus on:
- Risks and Challenges: Highlight factors like market saturation, financial instability, or macroeconomic threats that could hinder the stock's performance.
- Competitive Weaknesses: Emphasize vulnerabilities such as weaker market positioning, declining innovation, or threats from competitors.
- Negative Indicators: Use evidence from financial data, market trends, or recent adverse news to support your position.
- Bull Counterpoints: Critically analyze the bull argument with specific data and sound reasoning, exposing weaknesses or over-optimistic assumptions.
- Engagement: Present your argument in a conversational style, directly engaging with the bull analyst's points and debating effectively rather than simply listing facts.

Resources available:
Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Master analyst signals: {master_signals_text}
Conversation history of the debate: {history}
Last bull argument: {current_response}
Reflections from similar situations and lessons learned: {past_memory_str}

You have access to the following tools to support your argument with real-time data. Each tool is a specialized analyst skill that can provide specific insights:

{tool_descriptions}

If you need specific data to counter the bull's claims, call the appropriate tool. Use the tools when you need precise numbers or models. Do not call tools unnecessarily. Prioritize tools that are most relevant to the current debate topic.

Use this information to deliver a compelling bear argument, refute the bull's concerns, and engage in a dynamic debate that demonstrates the risks and weaknesses of investing in the stock. You must also address reflections and learn from lessons and mistakes you made in the past.
"""

        # ========== 核心修改：增强的工具使用引导 ==========
        system_message_v2 = f"""You are a Bear Analyst making the case against investing in the stock. Your goal is to present a well-reasoned argument emphasizing risks, challenges, and negative indicators. Leverage the provided research and data to highlight potential downsides and counter bullish arguments effectively.

Key points to focus on:
- Risks and Challenges: Highlight factors like market saturation, financial instability, or macroeconomic threats that could hinder the stock's performance.
- Competitive Weaknesses: Emphasize vulnerabilities such as weaker market positioning, declining innovation, or threats from competitors.
- Negative Indicators: Use evidence from financial data, market trends, or recent adverse news to support your position.
- Bull Counterpoints: Critically analyze the bull argument with specific data and sound reasoning, exposing weaknesses or over-optimistic assumptions.
- Engagement: Present your argument in a conversational style, directly engaging with the bull analyst's points and debating effectively rather than simply listing facts.

Resources available:
Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Master analyst signals: {master_signals_text}
Conversation history of the debate: {history}
Last bull argument: {current_response}
Reflections from similar situations and lessons learned: {past_memory_str}

You have access to the following tools to support your argument with real-time data. Each tool is a specialized analyst skill that can provide specific insights:

{tool_descriptions}

**Tool Usage Guidance:**
To build a more persuasive and data-backed bearish case, you are **strongly encouraged to call relevant tools** to obtain concrete numbers, independent valuations, or expert perspectives. For example:
- Call `valuation_analyst` to get an independent intrinsic value estimate that may contradict the bull's claims.
- Call `fundamental_analyst` to verify financial health metrics (ROE, margins, growth) that could reveal underlying weaknesses.
- Call `charlie_munger_analyst` or `warren_buffett_analyst` to invoke well-known principles that support a cautious or skeptical view.
- Call `sentiment_analyst` or `technical_analyst` to assess market sentiment or momentum that may favor the bear side.
- Call `news_sentiment_analyst` to obtain recent news sentiment that might be negative for the stock.

Using these tools demonstrates thorough analysis and provides quantitative evidence, making your argument much stronger. **At least one tool call is recommended** during your reasoning, but avoid calling tools that are not directly relevant to the current debate. Prioritize tools that address the specific claims made by the bull analyst.

Use this information to deliver a compelling bear argument, refute the bull's concerns, and engage in a dynamic debate that demonstrates the risks and weaknesses of investing in the stock. You must also address reflections and learn from lessons and mistakes you made in the past.
"""

        system_message = f"""You are a Bear Analyst making the case against investing in the stock. Your goal is to present a well-reasoned argument emphasizing risks, challenges, and negative indicators. Leverage the provided research and data to highlight potential downsides and counter bullish arguments effectively.

Key points to focus on:
- Risks and Challenges: Highlight factors like market saturation, financial instability, or macroeconomic threats that could hinder the stock's performance.
- Competitive Weaknesses: Emphasize vulnerabilities such as weaker market positioning, declining innovation, or threats from competitors.
- Negative Indicators: Use evidence from financial data, market trends, or recent adverse news to support your position.
- Bull Counterpoints: Critically analyze the bull argument with specific data and sound reasoning, exposing weaknesses or over-optimistic assumptions.
- Engagement: Present your argument in a conversational style, directly engaging with the bull analyst's points and debating effectively rather than simply listing facts.

Resources available:
Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Master analyst signals: {master_signals_text}
Conversation history of the debate: {history}
Last bull argument: {current_response}
Reflections from similar situations and lessons learned: {past_memory_str}

You have access to the following tools to support your argument with real-time data. Each tool is a specialized analyst skill that can provide specific insights:

{tool_descriptions}

**CRITICAL INSTRUCTION:**
Before you write your final bearish argument, you **MUST** call at least one tool to obtain additional data or perspective. This is mandatory to ensure your reasoning is data-driven and robust. 
- If you need valuation numbers, call `valuation_analyst`.
- If you need fundamental metrics (ROE, margins, growth), call `fundamental_analyst`.
- If you need a renowned investor's skeptical view, call `charlie_munger_analyst` or `warren_buffett_analyst`.
- If you need market sentiment or technicals, call `sentiment_analyst` or `technical_analyst`.
- If you need news sentiment, call `news_sentiment_analyst`.

**You must choose at least one tool that is directly relevant to the current debate. Failing to call any tool will weaken your argument. After receiving the tool results, incorporate them into your final response.**

Use this information to deliver a compelling bear argument, refute the bull's concerns, and engage in a dynamic debate that demonstrates the risks and weaknesses of investing in the stock. You must also address reflections and learn from lessons and mistakes you made in the past.
"""

        # ========== 5. 构建 Prompt 并绑定工具 ==========
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="messages"),
        ])
        chain = prompt | llm.bind_tools(tools)

        print("   🔧 Calling LLM with tool bindings...")

        # --- 调用 LLM ---
        result = chain.invoke({"messages": state["messages"]})
        new_messages = state["messages"] + [result]

        # --- 判断工具调用 ---
        if result.tool_calls:
            tool_names = [tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown') 
                          for tc in result.tool_calls]
            print(f"   ⚙️ Bear called tools: {tool_names}")
            print(f"[BEAR RESEARCHER] Waiting for tool results...\n")
            print(f"{'='*60}")
            return {
                "messages": new_messages,
                "investment_debate_state": state["investment_debate_state"],
            }
        else:
            argument = f"Bear Analyst: {result.content}"
            print(f"   💬 Bear argument generated (length: {len(result.content)} chars)")
            summary = result.content[:200].replace('\n', ' ') + ("..." if len(result.content) > 200 else "")
            print(f"   Summary: {summary}")
            
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
            }

    return bear_node
