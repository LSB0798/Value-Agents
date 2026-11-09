"""valueagents 全局配置真相源。

所有 secrets / URLs / timeouts / 路径的唯一来源。
只读不写：不修改 os.environ，不打印，不校验必填（留给下游判断）。

使用：
    from valueagents.settings import settings
    settings.finnhub_api_key
    settings.compress_api_url
    settings.log_dir / "valueagents.log"

本地开发：在项目根创建 .env，参考 .env.example
生产部署：通过环境变量注入（Docker env / k8s secret / systemd EnvironmentFile）
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


# ──────────────────────────────────────────────────────────────
# .env 加载：指定项目根，避免依赖当前工作目录
# ──────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DOTENV_PATH = _PROJECT_ROOT / ".env"

if _DOTENV_PATH.exists():
    load_dotenv(_DOTENV_PATH, override=False)
else:
    load_dotenv(override=False)   # 标准查找（cwd 及上游）


# ──────────────────────────────────────────────────────────────
# 环境变量解析助手（永不抛异常，缺失返回 default）
# ──────────────────────────────────────────────────────────────
def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _env_path(key: str, default: Path) -> Path:
    raw = os.environ.get(key, "").strip()
    return Path(raw).expanduser() if raw else default


def _ensure_dir(p: Path) -> Path:
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError:
        # 极端情况（只读文件系统）不阻断启动，交给下游报错
        pass
    return p


# ──────────────────────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────────────────────
_SECRET_HINTS = ("api_key", "secret", "password")
_SECRET_SUFFIXES = ("_token",)

def _is_secret(field_name: str) -> bool:
    n = field_name.lower()
    return any(h in n for h in _SECRET_HINTS) or any(n.endswith(s) for s in _SECRET_SUFFIXES)


@dataclass(frozen=True)
class Settings:
    """不可变配置快照。字段全部来自环境变量 / .env。"""

    # ── Data provider credentials ──
    financial_datasets_api_key: str
    finnhub_api_key: str
    alpha_vantage_api_key: str
    gnews_api_key: str
    roic_api_key: str

    # ── Data vendor selection（api.py 的 use_edgar() / use_yfinance()） ──
    use_edgar: bool
    use_yfinance: bool

    # ── Compression service（compress_utils.py） ──
    compress_api_url: str
    compress_model: str
    compress_api_key: str
    compress_timeout: int
    diagnostic_token_threshold: int

    # ── Embedding service（news_embedding.py） ──
    embedding_api_url: str
    embedding_model: str
    embedding_api_key: str
    embedding_timeout: float
    embedding_batch_size: int
    embedding_enabled: bool

    # ── LLM（OpenAI-compatible，本地 vllm 常设 "dummy"） ──
    openai_api_key: str

    # ── Paths ──
    log_dir: Path
    tmp_dir: Path

    def __repr__(self) -> str:
        parts = []
        for f in fields(self):
            v = getattr(self, f.name)
            if _is_secret(f.name):
                v = "***" if v else ""
            parts.append(f"{f.name}={v!r}")
        return f"Settings({', '.join(parts)})"

    def as_public_dict(self) -> dict[str, Any]:
        """脱敏后的 dict，用于日志 / :config 展示。"""
        out: dict[str, Any] = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if _is_secret(f.name):
                out[f.name] = "***" if v else ""
            elif isinstance(v, Path):
                out[f.name] = str(v)
            else:
                out[f.name] = v
        return out


# ──────────────────────────────────────────────────────────────
# 加载
# ──────────────────────────────────────────────────────────────
def _load() -> Settings:
    default_log_dir = _PROJECT_ROOT / "logs"
    default_tmp_dir = Path(tempfile.gettempdir()) / "valueagents"

    return Settings(
        # ── Data provider credentials（无硬编码默认值，缺失即空） ──
        financial_datasets_api_key=_env("FINANCIAL_DATASETS_API_KEY"),
        finnhub_api_key=_env("FINNHUB_API_KEY"),
        alpha_vantage_api_key=_env("ALPHA_VANTAGE_API_KEY"),
        gnews_api_key=_env("GNEWS_API_KEY"),
        roic_api_key=_env("ROIC_API_KEY"),

        # ── Data vendor selection（保持原默认：yfinance 走免费） ──
        use_edgar=_env_bool("USE_EDGAR", False),
        use_yfinance=_env_bool("USE_YFINANCE", False),

        # ── Compression service（默认值取自 compress_utils.get_compress_config） ──
        compress_api_url=_env("COMPRESS_API_URL", "http://10.20.223.82:61274/v1"),
        compress_model=_env("COMPRESS_MODEL", "qwen3_37"),
        compress_api_key=_env("COMPRESS_API_KEY", "EMPTY"),
        compress_timeout=_env_int("COMPRESS_TIMEOUT", 3600),
        diagnostic_token_threshold=_env_int("DIAGNOSTIC_TOKEN_THRESHOLD", 2048),

        # ── Embedding service（默认值取自 news_embedding._get_config） ──
        embedding_api_url=_env("EMBEDDING_API_URL", "http://10.10.29.53:8003/v1"),
        embedding_model=_env("EMBEDDING_MODEL", "qwen3-embedding-0.6b"),
        embedding_api_key=_env("EMBEDDING_API_KEY", "dummy"),
        embedding_timeout=_env_float("EMBEDDING_TIMEOUT", 30.0),
        embedding_batch_size=_env_int("EMBEDDING_BATCH_SIZE", 64),
        embedding_enabled=_env_bool("EMBEDDING_ENABLED", True),

        # ── LLM ──
        openai_api_key=_env("OPENAI_API_KEY", "dummy"),

        # ── Paths（自动 mkdir -p） ──
        log_dir=_ensure_dir(_env_path("VALUEAGENTS_LOG_DIR", default_log_dir)),
        tmp_dir=_ensure_dir(_env_path("VALUEAGENTS_TMP_DIR", default_tmp_dir)),
    )


settings = _load()


def reload() -> Settings:
    """仅用于测试：重新从环境变量加载（含 .env 强制覆盖）。"""
    global settings
    load_dotenv(_DOTENV_PATH if _DOTENV_PATH.exists() else None, override=True)
    settings = _load()
    return settings


__all__ = ["Settings", "settings", "reload", "_is_secret"]
