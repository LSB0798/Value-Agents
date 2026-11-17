# valueagents/agents/utils/compression_probe.py
"""4 层压缩器的统计上报，跑 2-3 次后删除。"""

def report_state(agent_name: str, state):
    if state is None:
        return
    s = state.stats
    total = sum(s.values())
    if total == 0:
        return
    print(f"   [COMPRESSION_STATS][{agent_name}] "
          f"L1_skip={s['L1_skipped']} L1_offload={s['L1_offloaded']} "
          f"L2_defer={s['L2_deferred']} L3_compress={s['L3_compressed']} "
          f"L4_fallback={s['L4_fallback']} L4_circuit={s['L4_circuit_open']} "
          f"total={total} budget={state.consumed_tokens}/{state.token_budget}")
