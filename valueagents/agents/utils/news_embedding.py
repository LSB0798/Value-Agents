# valueagents/agents/utils/news_embedding.py
"""
语义嵌入封装（Sprint 1）。

职责：
  - 通过 OpenAI 兼容接口调用 vLLM 上的 Qwen3-Embedding-0.6B
  - 内存缓存：规范化标题 -> 向量（避免重复编码）
  - 批量编码：一次请求最多 N 条
  - 降级：vLLM 不可达时返回 None，由 news_dedup 回退到字符 n-gram
  - 熔断：连续失败 MAX_FAILED_STREAK 次后不再尝试，避免每次成对循环都发请求

设计约束：
  - 不导入任何项目内模块（避免循环依赖）
  - 不修改任何现有调用方
  - 失败不抛异常，只返回 None
"""

from __future__ import annotations

import logging
import os
import re
import threading
from typing import Iterable, Optional

import numpy as np
import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 配置（环境变量优先）
# ---------------------------------------------------------------------------
def _get_config() -> dict:
    return {
        "base_url": os.environ.get("EMBEDDING_API_URL", "http://10.10.29.53:8003/v1"),
        "model": os.environ.get("EMBEDDING_MODEL", "qwen3-embedding-0.6b"),
        "api_key": os.environ.get("EMBEDDING_API_KEY", "dummy"),
        "timeout": float(os.environ.get("EMBEDDING_TIMEOUT", "30")),
        "batch_size": int(os.environ.get("EMBEDDING_BATCH_SIZE", "64")),
        "enabled": os.environ.get("EMBEDDING_ENABLED", "true").lower() == "true",
    }


# ---------------------------------------------------------------------------
# 内存缓存与熔断
# ---------------------------------------------------------------------------
_CACHE_LOCK = threading.Lock()
_VEC_CACHE: dict[str, np.ndarray] = {}   # key: 规范化标题 -> L2 归一化向量
_FAILED_STREAK = 0
_MAX_FAILED_STREAK = 3


_CLEAN_RE = re.compile(r"[^a-z0-9\u4e00-\u9fff]+")


def _cache_key(title: str) -> str:
    t = (title or "").lower()
    t = _CLEAN_RE.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def cache_size() -> int:
    with _CACHE_LOCK:
        return len(_VEC_CACHE)


def clear_cache() -> None:
    global _FAILED_STREAK
    with _CACHE_LOCK:
        _VEC_CACHE.clear()
        _FAILED_STREAK = 0


def _is_circuit_open() -> bool:
    with _CACHE_LOCK:
        return _FAILED_STREAK >= _MAX_FAILED_STREAK


def _mark_success() -> None:
    global _FAILED_STREAK
    with _CACHE_LOCK:
        _FAILED_STREAK = 0


def _mark_failure() -> None:
    global _FAILED_STREAK
    with _CACHE_LOCK:
        _FAILED_STREAK += 1


# ---------------------------------------------------------------------------
# vLLM 批量请求
# ---------------------------------------------------------------------------
def _embed_batch(texts: list[str]) -> Optional[np.ndarray]:
    """调用 vLLM embedding 接口，返回 (N, dim) 的 L2 归一化数组。失败返回 None。"""
    cfg = _get_config()
    if not cfg["enabled"]:
        return None

    url = f"{cfg['base_url'].rstrip('/')}/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['api_key']}",
    }
    payload = {"model": cfg["model"], "input": texts}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=cfg["timeout"])
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("[news_embedding] vLLM call failed: %s", e)
        return None

    items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
    if len(items) != len(texts):
        logger.warning(
            "[news_embedding] returned %d vectors for %d inputs",
            len(items), len(texts),
        )
        return None

    vecs = np.asarray([it["embedding"] for it in items], dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


# ---------------------------------------------------------------------------
# 带缓存 + 熔断的入口
# ---------------------------------------------------------------------------
def _infer_dim() -> int:
    with _CACHE_LOCK:
        for v in _VEC_CACHE.values():
            return int(v.shape[0])
    return 1024  # Qwen3-Embedding-0.6B 默认维度


def embed_texts(texts: Iterable[str]) -> Optional[np.ndarray]:
    """
    批量编码。返回与输入顺序一致的 (N, dim) L2 归一化矩阵。
    缓存命中则直接返回；缺失的批量请求 vLLM。
    若 vLLM 不可用（熔断或调用失败），返回 None。
    """
    text_list = list(texts)
    if not text_list:
        return np.zeros((0, _infer_dim()), dtype=np.float32)

    if _is_circuit_open():
        return None

    keys = [_cache_key(t) for t in text_list]

    # 找出未命中的（去重，保留首次出现顺序）
    miss_keys: list[str] = []
    miss_texts: list[str] = []
    seen: set[str] = set()
    with _CACHE_LOCK:
        for k, t in zip(keys, text_list):
            if k in _VEC_CACHE or k in seen:
                continue
            seen.add(k)
            miss_keys.append(k)
            miss_texts.append(t)

    # 批量请求缺失部分
    if miss_texts:
        cfg = _get_config()
        bs = max(1, cfg["batch_size"])
        new_vectors: dict[str, np.ndarray] = {}
        any_success = False
        for start in range(0, len(miss_texts), bs):
            chunk_keys = miss_keys[start:start + bs]
            chunk_texts = miss_texts[start:start + bs]
            vecs = _embed_batch(chunk_texts)
            if vecs is None:
                continue
            any_success = True
            for k, v in zip(chunk_keys, vecs):
                new_vectors[k] = v

        if new_vectors:
            with _CACHE_LOCK:
                _VEC_CACHE.update(new_vectors)

        if not any_success:
            _mark_failure()
            logger.warning(
                "[news_embedding] all batches failed, streak=%d", _FAILED_STREAK
            )
            return None
        _mark_success()

    # 组装结果
    out = np.zeros((len(text_list), _infer_dim()), dtype=np.float32)
    with _CACHE_LOCK:
        for i, k in enumerate(keys):
            v = _VEC_CACHE.get(k)
            if v is None:
                return None
            out[i] = v
    return out


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------
def title_similarity_semantic(title1: str, title2: str) -> Optional[float]:
    """
    语义相似度。成功返回 [0,1]；vLLM 不可用时返回 None。
    """
    vecs = embed_texts([title1, title2])
    if vecs is None or vecs.shape[0] != 2:
        return None
    sim = float(np.dot(vecs[0], vecs[1]))
    return max(0.0, min(1.0, sim))


def precompute_for_items(items: Iterable) -> bool:
    """
    批量预编码一组 NewsItem 的标题，预热缓存。
    返回 True 表示预热成功（或无需预热）；False 表示 vLLM 不可用。
    """
    titles = [getattr(it, "title", "") for it in items if getattr(it, "title", None)]
    if not titles:
        return True
    return embed_texts(titles) is not None


__all__ = [
    "title_similarity_semantic",
    "precompute_for_items",
    "embed_texts",
    "cache_size",
    "clear_cache",
]
