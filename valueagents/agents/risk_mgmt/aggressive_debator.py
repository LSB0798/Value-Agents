

def create_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        # ========== 节点入口 ==========
        risk_debate_state = state["risk_debate_state"]
        current_round = risk_debate_state.get("count", 0) // 3 + 1
        print(f"\n{'='*60}")
        print(f"🔴 [AGGRESSIVE RISK ANALYST] Round {current_round}")
        # print(f"{'='*60}")
        # ================================

        history = risk_debate_state.get("history", "")
        aggressive_history = risk_debate_state.get("aggressive_history", "")

        current_conservative_response = risk_debate_state.get("current_conservative_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        # ========== 打印收到的其他分析师论点 ==========
        if current_conservative_response:
            print(f"   📩 Received Conservative argument: {current_conservative_response[:150].replace(chr(10), ' ')}...")
        else:
            print("   📩 No Conservative argument yet")
        if current_neutral_response:
            print(f"   📩 Received Neutral argument: {current_neutral_response[:150].replace(chr(10), ' ')}...")
        else:
            print("   📩 No Neutral argument yet")
        # ===============================================

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # ========== 打印交易员决策摘要 ==========
        print(f"   📋 Trader decision: {trader_decision[:150].replace(chr(10), ' ')}..." if trader_decision else "   📋 No trader decision available")
        # ========================================

        prompt = f"""As the Aggressive Risk Analyst, your role is to actively champion high-reward, high-risk opportunities, emphasizing bold strategies and competitive advantages. When evaluating the trader's decision or plan, focus intently on the potential upside, growth potential, and innovative benefits—even when these come with elevated risk. Use the provided market data and sentiment analysis to strengthen your arguments and challenge the opposing views. Specifically, respond directly to each point made by the conservative and neutral analysts, countering with data-driven rebuttals and persuasive reasoning. Highlight where their caution might miss critical opportunities or where their assumptions may be overly conservative. Here is the trader's decision:

{trader_decision}

Your task is to create a compelling case for the trader's decision by questioning and critiquing the conservative and neutral stances to demonstrate why your high-reward perspective offers the best path forward. Incorporate insights from the following sources into your arguments:

Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}
Here is the current conversation history: {history} Here are the last arguments from the conservative analyst: {current_conservative_response} Here are the last arguments from the neutral analyst: {current_neutral_response}. If there are no responses from the other viewpoints yet, present your own argument based on the available data.

Engage actively by addressing any specific concerns raised, refuting the weaknesses in their logic, and asserting the benefits of risk-taking to outpace market norms. Maintain a focus on debating and persuading, not just presenting data. Challenge each counterpoint to underscore why a high-risk approach is optimal. Output conversationally as if you are speaking without any special formatting."""

        response = llm.invoke(prompt)

        argument = f"Aggressive Analyst: {response.content}"

        # ========== 打印生成的论点摘要 ==========
        print(f"   💬 Generated argument (length: {len(response.content)} chars)")
        print(f"   Summary: {response.content[:200].replace(chr(10), ' ')}...")
        # ========================================

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": aggressive_history + "\n" + argument,
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Aggressive",
            "current_aggressive_response": argument,
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        print(f"[AGGRESSIVE RISK ANALYST] Done.\n")
        # ===== 添加报告摘要打印 =====
        # print(f"   📄 Return (new_risk_debate_state: {new_risk_debate_state})")
        # ===========================
        print(f"{'='*60}")

        return {"risk_debate_state": new_risk_debate_state}

    return aggressive_node
