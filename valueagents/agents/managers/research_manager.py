# ./valueagents/agents/managers/research_manager.py
import time
from valueagents.agents.utils.agent_utils import build_instrument_context

def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        print(f"\n{'='*60}")
        print(f"🧠 [RESEARCH MANAGER] Synthesizing investment debate")
        print(f"{'='*60}")
        print(f"   Company: {state['company_of_interest']}")
        print(f"   Debate history length: {len(state['investment_debate_state'].get('history', ''))} chars")
        reports = ['market_report', 'sentiment_report', 'news_report', 'fundamentals_report']
        for r in reports:
            if state.get(r):
                print(f"   Input {r}: {len(state[r])} chars")
        
        instrument_context = build_instrument_context(state["company_of_interest"])
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""As the portfolio manager and debate facilitator, your role is to critically evaluate this round of debate and make a definitive decision: align with the bear analyst, the bull analyst, or choose Hold only if it is strongly justified based on the arguments presented.

Summarize the key points from both sides concisely, focusing on the most compelling evidence or reasoning. Your recommendation—Buy, Sell, or Hold—must be clear and actionable. Avoid defaulting to Hold simply because both sides have valid points; commit to a stance grounded in the debate's strongest arguments.

Additionally, develop a detailed investment plan for the trader. This should include:

Your Recommendation: A decisive stance supported by the most convincing arguments.
Rationale: An explanation of why these arguments lead to your conclusion.
Strategic Actions: Concrete steps for implementing the recommendation.
Take into account your past mistakes on similar situations. Use these insights to refine your decision-making and ensure you are learning and improving. Present your analysis conversationally, as if speaking naturally, without special formatting. 

Here are your past reflections on mistakes:
\"{past_memory_str}\"

{instrument_context}

Here is the debate:
Debate History:
{history}"""
        print(f"   Prompt length: {len(prompt)} chars")
        response = llm.invoke(prompt)
        print(f"   📋 Investment plan generated (length: {len(response.content)} chars)")
        print(f"   Plan summary: {response.content[:200].replace(chr(10), ' ')}...")
        print(f"[RESEARCH MANAGER] Done.\n")

        new_investment_debate_state = {
            "judge_decision": response.content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": response.content,
            "count": investment_debate_state["count"],
        }

        # ===== 添加报告摘要打印 =====
        # print(f"   📄 Return (new_investment_debate_state: {new_investment_debate_state})")
        # print(f"   📄 Return (investment_plan: {response.content})")
        # ===========================

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": response.content,
        }

    return research_manager_node
