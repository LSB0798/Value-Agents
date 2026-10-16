# ./valueagents/agents/trader/trader.py
import functools

from valueagents.agents.utils.agent_utils import build_instrument_context


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        instrument_context = build_instrument_context(company_name)
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # ---------- 入口打印 ----------
        print(f"\n{'='*60}")
        print(f"💼 [TRADER] Generating trading plan for {company_name}")
        # print(f"{'='*60}")
        if investment_plan:
            print(f"   Input investment plan (length: {len(investment_plan)} chars)")
            print(f"   Plan preview: {investment_plan[:150].replace(chr(10), ' ')}...")
        else:
            print("   No investment plan provided.")
        # 报告长度信息
        reports = {
            "Market": market_research_report,
            "Sentiment": sentiment_report,
            "News": news_report,
            "Fundamentals": fundamentals_report
        }
        for name, report in reports.items():
            if report:
                print(f"   {name} report length: {len(report)} chars")
        # -------------------------

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        context = {
            "role": "user",
            "content": f"Based on a comprehensive analysis by a team of analysts, here is an investment plan tailored for {company_name}. {instrument_context} This plan incorporates insights from current technical market trends, macroeconomic indicators, and social media sentiment. Use this plan as a foundation for evaluating your next trading decision.\n\nProposed Investment Plan: {investment_plan}\n\nLeverage these insights to make an informed and strategic decision.",
        }

        messages = [
            {
                "role": "system",
                "content": f"""You are a trading agent analyzing market data to make investment decisions. Based on your analysis, provide a specific recommendation to buy, sell, or hold. End with a firm decision and always conclude your response with 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**' to confirm your recommendation. Apply lessons from past decisions to strengthen your analysis. Here are reflections from similar situations you traded in and the lessons learned: {past_memory_str}""",
            },
            context,
        ]

        result = llm.invoke(messages)

        # ---------- 输出打印 ----------
        plan_content = result.content
        print(f"   📋 Trader plan generated (length: {len(plan_content)} chars)")
        # 提取最终建议（可能包含在文本中，简单提取前200字符）
        print(f"   Plan preview: {plan_content[:200].replace(chr(10), ' ')}...")
        print(f"[TRADER] Done.\n")
        # -------------------------

        print(f"{'='*60}")

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
