#!/usr/bin/env python
# scripts/keepalive.py
"""
Keepalive Daemon — Phase 0

约束：GPU 不能空闲，否则会被收回。本 daemon 周期性发小请求保活。

模式（通过 `tmp/keepalive_mode.txt` 动态切换）：
    dev    → 3 min   （默认，开发期）
    reg    → 15 min  （regression 期间降频）
    quiet  → 15 min  （夜间/低占用）

用法：
    python scripts/keepalive.py                    # 默认 dev
    python scripts/keepalive.py --interval 3       # 手动指定分钟
    python scripts/keepalive.py --once             # 跑一次就退出（调试用）

后台运行：
    nohup python scripts/keepalive.py > tmp/keepalive.log 2>&1 &
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

KEEPALIVE_MODE_FILE = _REPO_ROOT / "tmp" / "keepalive_mode.txt"

MODE_INTERVALS = {
    "dev": 3,
    "reg": 15,
    "quiet": 15,
}

DEFAULT_BASE_URL = "http://10.20.223.75:8001/v1"
DEFAULT_MODEL = "qwen3.6-27B"
PROMPT = "Reply with only the word: pong"


def read_mode() -> str:
    if KEEPALIVE_MODE_FILE.exists():
        mode = KEEPALIVE_MODE_FILE.read_text().strip()
        if mode in MODE_INTERVALS:
            return mode
    return "dev"


def get_interval(default_interval: int | None) -> tuple[int, str]:
    if default_interval is not None:
        return default_interval, "manual"
    mode = read_mode()
    return MODE_INTERVALS[mode], mode


def ping(llm) -> tuple[bool, float]:
    t0 = time.time()
    try:
        resp = llm.invoke(PROMPT)
        content = getattr(resp, "content", str(resp))
        return bool(content), time.time() - t0
    except Exception as e:
        print(f"    ping error: {type(e).__name__}: {e}")
        return False, time.time() - t0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=None,
                        help="覆盖 mode，强制固定 interval（分钟）")
    parser.add_argument("--once", action="store_true", help="跑一次就退出")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    # 延迟 import，避免每次启动都加载 LLM
    from langchain_openai import ChatOpenAI
    import os
    os.environ.setdefault("OPENAI_API_KEY", "dummy")

    llm = ChatOpenAI(
        model=args.model,
        openai_api_key="dummy",
        openai_api_base=args.base_url,
        temperature=0.0,
        request_timeout=30,
    )

    print(f"[keepalive] started  base_url={args.base_url} model={args.model}")
    print(f"[keepalive] mode_file={KEEPALIVE_MODE_FILE}")

    KEEPALIVE_MODE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if args.once:
        ok, dt = ping(llm)
        print(f"[keepalive] once: ok={ok} elapsed={dt:.2f}s")
        return

    while True:
        try:
            interval, mode = get_interval(args.interval)
            t0 = time.time()
            ok, dt = ping(llm)
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] mode={mode} interval={interval}min ok={ok} ping={dt:.2f}s")

            sleep_sec = max(5, interval * 60 - (time.time() - t0))
            # 每 30 秒检查一次 mode 文件（支持动态切换）
            while sleep_sec > 0:
                time.sleep(min(30, sleep_sec))
                sleep_sec -= 30
                new_interval, _ = get_interval(args.interval)
                if new_interval != interval:
                    print(f"[keepalive] mode changed → interval={new_interval}min, restarting sleep")
                    break
        except KeyboardInterrupt:
            print("\n[keepalive] Ctrl+C, exiting")
            break
        except Exception as e:
            print(f"[keepalive] unexpected error: {type(e).__name__}: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
