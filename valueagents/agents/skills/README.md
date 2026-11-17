# Skills 目录结构

本目录包含 29 个 skill（19 master + 10 core）及其框架代码。

## 分层

### 框架代码（直接位于本目录的 .py）
- `loader.py`     — 从 SKILL.md + skill.py 动态加载单个 skill
- `registry.py`   — 全局 SkillRegistry 单例
- `base.py`       — master skill 共享工具（build_minimal_agent_state / extract_signal_from_state）
- `contract.py`   — SkillKind / SkillContext / SkillResult / SkillManifest
- `runtime.py`    — core skill 的 tool loop 与 contextvars

### 19 个 master skill（根目录 <name>_skill/ 子目录）
每个子目录包含 SKILL.md + skill.py。
由 `loader.py::load_all_skills` 遍历根目录时加载。
调用接口：`tool.func(ticker, end_date, api_key) -> JSON str`

清单：
- ben_graham_skill, warren_buffett_skill, charlie_munger_skill, peter_lynch_skill,
  phil_fisher_skill, bill_ackman_skill, michael_burry_skill, aswath_damodaran_skill,
  mohnish_pabrai_skill, nassim_taleb_skill, cathie_wood_skill, stanley_druckenmiller_skill,
  rakesh_jhunjhunwala_skill, fundamental_skill, growth_skill, news_sentiment_skill,
  sentiment_skill, technical_skill, valuation_skill

### 9 个 core skill（core/ 子目录）
由 `core/__init__.py::load_core_skill` 单独加载。
调用接口：`skill.execute(SkillContext) -> SkillResult`

清单：
- market_analyst_skill, social_analyst_skill, news_analyst_skill,
  fundamentals_analyst_skill, trader_skill, research_manager_skill,
  portfolio_manager_skill, research_team_skill（meta）, risk_team_skill（meta）,
  master_team_skill（meta）

### policies/（非 skill）
- debate.py — 辩论停止判据（DebatePolicy.should_stop_risk）

## 加载逻辑速查

```python
# master（19 个）：遍历 skills/ 根目录，跳过 core/policies/__pycache__ 等
load_all_skills(skills_root):
    for subdir in skills_root.iterdir():
        if subdir.name in {"core", "policies", "__pycache__"}:
            continue
        if subdir.is_dir() and not subdir.name.startswith("__") and not subdir.name.startswith("."):
            load_skill(subdir)

# core（10 个）：单独从 core/<name>/ 加载，支持 leaf 和 meta 两种 kind
load_core_skill(name):
    ...
```

## 为什么 master 在根、core 在 core/

- master 是“独立评分单元”，数量多（19）、结构统一，放在根目录让 `load_all_skills` 一次遍历即可
- core 是“流程模块”，有 meta 子类型、有 `SkillContext` 接口，需要单独的加载和校验逻辑，放在子目录便于区分