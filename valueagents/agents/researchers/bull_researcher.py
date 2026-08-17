# valueagents/agents/researchers/bull_researcher.py

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pathlib import Path
from valueagents.agents.skills.loader import load_skill
from valueagents.agents.skills.loader import load_all_skills

# added prints for master_signals

def create_bull_researcher(llm, memory):
    # --- 加载所有 Skills 作为工具 ---
    # 自动扫描 skills/ 目录下所有符合规范的 Skill
    all_skills = load_all_skills()  # 返回 List[StructuredTool]
    
    # 可选：按需过滤，例如排除某些 Skill（如果不想全部暴露）
    # 这里默认全部加载
    tools = all_skills

    # 打印加载的工具名称（便于调试）
    print(f"[Bull Researcher] Loaded {len(tools)} tools: {[t.name for t in tools]}")

    def bull_node(state) -> dict:
        # ========== 1. 节点入口打印（已有，补充轮次信息） ==========
        current_round = state["investment_debate_state"].get("count", 0) // 2 + 1
        print(f"\n{'='*60}")
        print(f"🐂 [BULL RESEARCHER] Round {current_round}")
        # print(f"{'='*60}")

        ###################################################################################
        ################################### added prints ###################################
        print("\n🐂 BULL RESEARCHER: Starting debate round...") #################### added prints
        # 获取大师信号并打印
        master_signals = state.get("master_analyst_signals", {})
        if master_signals:
            print("   📚 Using master analyst signals:")
            for agent, signals in master_signals.items():
                for ticker, sig in signals.items():
                    print(f"      - {agent}: {ticker} -> {sig.get('signal')} (conf: {sig.get('confidence')})")
        else:
            print("   ⚠️ No master analyst signals available.")
        ################################### added prints ###################################
        ####################################################################################

        # ========== 3. 提取状态数据（原有代码） ==========
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")
        current_response = investment_debate_state.get("current_response", "")

        # ========== 2. 打印对方（熊）的论点 ==========
        if current_response:
            # 提取论点内容（去掉"Bear Analyst:"前缀）
            content = current_response.replace("Bear Analyst:", "").strip()
            print(f"   📩 Received Bear argument: {content[:150].replace(chr(10), ' ')}...")
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
        master_signals = state.get("master_analyst_signals", {}) # CONTENT-01
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

        # ========== 4. 构建系统提示 ==========
        # 动态生成工具列表描述
        tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])

        system_message = f"""You are a Bull Analyst advocating for investing in the stock. Your task is to build a strong, evidence-based case emphasizing growth potential, competitive advantages, and positive market indicators. Leverage the provided research and data to address concerns and counter bearish arguments effectively.

Key points to focus on:
- Growth Potential: Highlight the company's market opportunities, revenue projections, and scalability.
- Competitive Advantages: Emphasize factors like unique products, strong branding, or dominant market positioning.
- Positive Indicators: Use financial health, industry trends, and recent positive news as evidence.
- Bear Counterpoints: Critically analyze the bear argument with specific data and sound reasoning, addressing concerns thoroughly and showing why the bull perspective holds stronger merit.
- Engagement: Present your argument in a conversational style, engaging directly with the bear analyst's points and debating effectively rather than just listing data.

Resources available:
Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Master analyst signals: {master_signals_text}
Conversation history of the debate: {history}
Last bear argument: {current_response}
Reflections from similar situations and lessons learned: {past_memory_str}

You have access to the following tools to support your argument with real-time data. Each tool is a specialized analyst skill that can provide specific insights:

{tool_descriptions}

If you need specific data to counter the bear's claims, call the appropriate tool. Use the tools when you need precise numbers or models. Do not call tools unnecessarily. Prioritize tools that are most relevant to the current debate topic.

Use this information to deliver a compelling bull argument, refute the bear's concerns, and engage in a dynamic debate that demonstrates the strengths of the bull position. You must also address reflections and learn from lessons and mistakes you made in the past.
"""

        # --- 构建 ChatPromptTemplate 并绑定工具 ---
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="messages"),
        ])
        chain = prompt | llm.bind_tools(tools)

        print("   🔧 Calling LLM with tool bindings...")

        # --- 调用 LLM，传入当前消息历史 ---
        result = chain.invoke({"messages": state["messages"]})

        # --- 将结果追加到消息历史 ---
        new_messages = state["messages"] + [result]

        # --- 判断是否有工具调用 ---
        if result.tool_calls:
            # 有工具调用
            tool_names = [tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown') 
                          for tc in result.tool_calls]
            print(f"   ⚙️ Bull called tools: {tool_names}")
            print(f"[BULL RESEARCHER] Waiting for tool results...\n")
            print(f"{'='*60}")
            # 有工具调用：返回新消息，但暂不更新辩论状态（等待工具执行）
            return {
                "messages": new_messages,
                "investment_debate_state": state["investment_debate_state"],
            }
        else:
            # 无工具调用：生成最终回复，更新辩论状态
            argument = f"Bull Analyst: {result.content}"
            print(f"   💬 Bull argument generated (length: {len(result.content)} chars)")
            # 打印论点摘要（前200字符）
            summary = result.content[:200].replace('\n', ' ') + ("..." if len(result.content) > 200 else "")
            print(f"   Summary: {summary}")

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
            }

    return bull_node