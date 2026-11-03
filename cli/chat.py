# cli/chat.py
"""
Chat 模式 REPL 入口（阶段 5）。

用法：
    python cli/main.py analyze --mode chat

交互流程：
  1. 一次性选择：ticker / date / 输出语言 / provider / model
  2. 构造 registry + llm + memory_bag
  3. 构造 ConversationalOrchestrator
  4. REPL 循环：读用户输入 → orchestrator.run() → 渲染 Markdown 结果

REPL 命令：
  exit / quit / :q    退出
  :help / ?           显示帮助
  :config             显示当前配置
  :new                重新选择 ticker / date
  其他                 作为 user query 调用 orchestrator
"""

from __future__ import annotations

import os
from typing import Any, Optional

import questionary
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from cli.utils import (
    get_ticker,
    get_analysis_date,
    ask_output_language,
    select_llm_provider,
    select_shallow_thinking_agent,
    select_deep_thinking_agent,
    select_research_depth,
    select_master_analysts,
)
from valueagents.agents.skills.registry import get_registry
from valueagents.agents.utils.memory import FinancialSituationMemory
from valueagents.llm_clients import create_llm_client
from valueagents.default_config import DEFAULT_CONFIG
from valueagents.orchestrators.conversational import ConversationalOrchestrator


console = Console()

_PROMPT = "你 > "

_HELP_TEXT = """\
[bold]Commands[/bold]
  :help, ?       显示本帮助
  :config        显示当前配置
  :new           重新选择 ticker / date
  :clear         （无操作）提示每轮对话独立
  exit, quit, :q 退出

[bold]Examples[/bold]
  只跑 Buffett 分析一下
  帮我做完整的分析
  先看 market 和 news，再出 research
  直接给我 portfolio decision（会被拒绝，因为前置缺失）
"""


# ============================================================
# 配置构造
# ============================================================
def _chat_selections() -> dict[str, Any]:
    """交互式收集 chat 模式参数（复用 cli/utils.py 的 selector）。"""
    console.print(Panel(
        "[bold cyan]Chat Mode Setup[/bold cyan]\n"
        "[dim]首次设置，之后的每轮对话都基于这份配置[/dim]",
        border_style="cyan",
    ))

    ticker = get_ticker()
    end_date = get_analysis_date()
    output_language = ask_output_language()

    # 🆕 加 research depth
    console.print(Panel(
        "[bold cyan]Research Depth[/bold cyan]",
        border_style="cyan",
    ))
    research_depth = select_research_depth()

    # 🆕 选大师（可跳过，默认 3 个）
    console.print(Panel(
        "[bold cyan]Master Analysts (Optional)[/bold cyan]\n"
        "[dim]Select 3-5 to run as independent analysts alongside the 4 core analysts[/dim]",
        border_style="cyan",
    ))
    master_analysts = select_master_analysts()

    # 复用 graph 模式的 provider 选择（会设置 OPENAI_API_KEY=dummy + 缓存模型名）
    provider, base_url = select_llm_provider()
    model = select_shallow_thinking_agent(provider)

    return {
        "ticker": ticker,
        "end_date": end_date,
        "output_language": output_language,
        "research_depth": research_depth,
        "master_analysts": master_analysts,
        "llm_provider": provider.lower(),
        "backend_url": base_url,
        "model": model,
    }


_DEPTH_TO_ROUND_BOUNDS = {     # 🆕 模块级常量（与 graph 模式一致）
    1: (1, 2),   # Shallow
    3: (2, 4),   # Medium
    5: (3, 8),   # Deep
}
def _build_config(selections: dict[str, Any]) -> dict[str, Any]:
    """构造 config（与 graph 模式的 DEFAULT_CONFIG + 覆盖一致）。"""
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = selections["llm_provider"]
    config["backend_url"] = selections["backend_url"]
    config["quick_think_llm"] = selections["model"]
    config["deep_think_llm"] = selections["model"]
    config["output_language"] = selections["output_language"]

    # 🆕 depth → 3 个 config 字段
    depth = selections.get("research_depth", 1)
    min_r, max_r = _DEPTH_TO_ROUND_BOUNDS.get(depth, (1, 2))
    config["min_debate_rounds"] = min_r
    config["max_debate_rounds"] = max_r
    config["max_risk_discuss_rounds"] = depth     # risk rounds = depth

    config["master_analysts"] = selections.get("master_analysts", [])
    
    return config


def _build_memory_bag(config: dict[str, Any]) -> dict[str, Any]:
    """构造 5 个 memory（与 graph 模式一致，供 core skill 内部 reflection 用）。"""
    return {
        "_bull_memory": FinancialSituationMemory("bull_memory", config),
        "_bear_memory": FinancialSituationMemory("bear_memory", config),
        "_trader_memory": FinancialSituationMemory("trader_memory", config),
        "_invest_judge_memory": FinancialSituationMemory("invest_judge_memory", config),
        "_portfolio_manager_memory": FinancialSituationMemory("portfolio_manager_memory", config),
    }


def _build_orchestrator(config: dict[str, Any]) -> ConversationalOrchestrator:
    """构造 Orchestrator：registry + llm + memory_bag。"""
    registry = get_registry()

    client = create_llm_client(
        provider=config["llm_provider"],
        model=config["quick_think_llm"],
        base_url=config.get("backend_url"),
    )
    llm = client.get_llm()

    memory_bag = _build_memory_bag(config)

    return ConversationalOrchestrator(
        registry=registry,
        llm=llm,
        config=config,
        max_steps=20,
        memory_bag=memory_bag,
        include_master_in_prompt=True,
        verbose=True,
    )


# ============================================================
# REPL 命令处理
# ============================================================
def _show_config(selections: dict[str, Any], config: dict[str, Any]) -> None:
    masters = selections.get("master_analysts", [])
    masters_str = ", ".join(masters) if masters else "(none, will use default 3)"

    console.print(Panel(
        f"[bold]Ticker[/bold]: {selections['ticker']}\n"
        f"[bold]Date[/bold]: {selections['end_date']}\n"
        f"[bold]Language[/bold]: {selections['output_language']}\n"
        f"[bold]Research Depth[/bold]: {selections.get('research_depth', 'N/A')}\n"
        f"[bold]Master Analysts[/bold]: {masters_str}\n"
        f"[bold]Provider[/bold]: {config['llm_provider']}\n"
        f"[bold]Model[/bold]: {config['quick_think_llm']}\n"
        f"[bold]Backend URL[/bold]: {config['backend_url']}\n"
        f"[bold]Debate rounds[/bold]: "
        f"min={config['min_debate_rounds']} / max={config['max_debate_rounds']}\n"
        f"[bold]Risk rounds[/bold]: {config['max_risk_discuss_rounds']}",
        title="Chat Mode Config",
        border_style="blue",
    ))


def _read_user_input() -> Optional[str]:
    """读取一行用户输入；Ctrl+C / Ctrl+D 返回 None。"""
    try:
        text = questionary.text(_PROMPT, qmark="", style=questionary.Style([
            ("text", "fg:green"),
            ("highlighted", "noinherit"),
        ])).ask()
    except (KeyboardInterrupt, EOFError):
        return None
    return text


# ============================================================
# 主入口
# ============================================================
def run_chat() -> None:
    """Chat 模式 REPL 主循环。"""
    os.environ.setdefault("OPENAI_API_KEY", "dummy")

    console.print(Panel(
        "[bold green]ValueAgents — Chat Mode[/bold green]\n"
        "[dim]对话式 skill 调度：可以只跑单个 skill，也可以编排完整流程[/dim]\n\n"
        "[dim]输入 [bold]:help[/bold] 查看命令，[bold]:new[/bold] 切换 ticker，[bold]exit[/bold] 退出[/dim]",
        border_style="green",
    ))

    # 一次性设置
    try:
        selections = _chat_selections()
    except (KeyboardInterrupt, EOFError, SystemExit):
        console.print("\n[yellow]Setup cancelled.[/yellow]")
        return

    config = _build_config(selections)
    orchestrator = _build_orchestrator(config)

    _show_config(selections, config)
    console.print()

    # REPL 循环
    while True:
        line = _read_user_input()
        if line is None:
            console.print("\n[dim]Bye.[/dim]")
            break

        line = line.strip()
        if not line:
            continue

        # ----- 命令 -----
        lower = line.lower()

        if lower in ("exit", "quit", ":q"):
            console.print("[dim]Bye.[/dim]")
            break

        if lower in (":help", "?", "help"):
            console.print(_HELP_TEXT)
            continue

        if lower == ":config":
            _show_config(selections, config)
            continue

        if lower == ":new":
            console.print("[cyan]Reconfigure ticker/date/masters...[/cyan]")
            try:
                ticker = get_ticker()
                end_date = get_analysis_date()
                selections["ticker"] = ticker
                selections["end_date"] = end_date
                reselect = questionary.confirm("Reselect master analysts?", default=False).ask()
                if reselect:
                    selections["master_analysts"] = select_master_analysts()
                    config = _build_config(selections)   # 同步更新 config
                console.print(f"[green]Updated: {ticker} @ {end_date}[/green]")
            except (KeyboardInterrupt, EOFError, SystemExit):
                console.print("[yellow]Reconfigure cancelled.[/yellow]")
            continue

        if lower == ":clear":
            console.print(
                "[dim]Note: each query is independent — artifacts do not carry over "
                "between queries. To reuse artifacts, phrase a single compound request.[/dim]"
            )
            continue

        # ----- 普通 query → 调 orchestrator -----
        try:
            answer = orchestrator.run(
                user_query=line,
                ticker=selections["ticker"],
                end_date=selections["end_date"],
            )
        except Exception as e:
            console.print(Panel(
                f"[red]Orchestrator error: {type(e).__name__}: {e}[/red]",
                border_style="red",
            ))
            continue

        # 渲染结果（Markdown 支持）
        console.print()
        console.print(Panel(
            Markdown(answer),
            title="Assistant",
            border_style="green",
            padding=(1, 2),
        ))
        console.print()
