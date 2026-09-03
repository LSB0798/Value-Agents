# valueagents/agents/utils/compress_utils.py

import os
import re
from typing import Optional
from openai import OpenAI

# 估算平均 token/word 比率（英文约 1.3，中文约 1.8，这里采用保守值 2.0）
TOKEN_PER_WORD = 2.0

# 模块级单例客户端缓存
_client_cache = {}

def get_compress_config_83():
    """从环境变量读取压缩服务配置"""
    return {
        "base_url": os.environ.get("COMPRESS_API_URL", "/v1"),
        "model": os.environ.get("COMPRESS_MODEL", "qwen3_32B"),
        "api_key": os.environ.get("COMPRESS_API_KEY", "EMPTY"),
        "timeout": int(os.environ.get("COMPRESS_TIMEOUT", "3600")),
    }

def get_compress_config():
    """从环境变量读取压缩服务配置"""
    return {
        "base_url": os.environ.get("COMPRESS_API_URL", "/v1"),
        "model": os.environ.get("COMPRESS_MODEL", "qwen3.6-27B"),
        "api_key": os.environ.get("COMPRESS_API_KEY", "EMPTY"),
        "timeout": int(os.environ.get("COMPRESS_TIMEOUT", "30")),
    }

def _get_client(config: dict) -> OpenAI:
    """获取或创建缓存的 OpenAI 客户端"""
    key = f"{config['base_url']}:{config['model']}"
    if key not in _client_cache:
        _client_cache[key] = OpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"],
            timeout=config.get("timeout", 3600)
        )
    return _client_cache[key]


def estimate_word_count_v0(text: str) -> int:
    """
    兼容中英文的混合字数估算。
    - 中文字符（含标点、数字、符号）：每个算 1 字
    - 英文单词：每个算 1 词
    """
    text = text.strip()
    if not text:
        return 0
    # 英文单词数
    en_words = len(re.findall(r'[a-zA-Z]+', text))
    # 移除英文单词和所有空白后，剩余每个字符各算 1 字
    non_en = re.sub(r'[a-zA-Z]+|\s+', '', text)
    return en_words + len(non_en)


def estimate_word_count(text: str) -> int:
    """
    兼容中英文、数字及常见金融格式的混合字数估算。
    
    规则（按优先级顺序匹配，避免重复计数）：
    - 日期格式（YYYY-MM-DD, YYYY/MM/DD）：每个算 1 个单位
    - 百分比/倍数（如 25.3%, 1.5x, 100x）：每个算 1 个单位
    - 英文单词（含撇号缩写，如 don't / AAPL's）：每个算 1 词
    - 中文字符（CJK Unified Ideographs）：每个算 1 字
    - 数字序列（含千分位、小数点，如 1,234.56）：每个算 1 个单位
    - 标点、符号、空白、货币符号：不计入
    """
    text = text.strip()
    if not text:
        return 0

    count = 0

    # 1. 日期格式（YYYY-MM-DD 或 YYYY/MM/DD）
    # 先计数并替换，避免被拆成多个数字
    date_pattern = r'\d{4}[-/]\d{1,2}[-/]\d{1,2}'
    dates = re.findall(date_pattern, text)
    count += len(dates)
    text = re.sub(date_pattern, ' ', text)

    # 2. 百分比/倍数（如 25.3%, 1.5x, 100x, 15%）
    # 先计数并替换，避免数字和字母被分开计数
    pct_pattern = r'\d+(?:[,.]\d+)*[xX%％]'
    pcts = re.findall(pct_pattern, text)
    count += len(pcts)
    text = re.sub(pct_pattern, ' ', text)

    # 3. 英文单词（含撇号缩写）
    en_words = len(re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text))
    count += en_words

    # 4. 中文字符
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    count += chinese_chars

    # 5. 剩余数字序列（含千分位、小数点）
    numbers = len(re.findall(r"\d+(?:[,.]\d+)*", text))
    count += numbers

    return count


def safe_truncate(text: str, max_chars: int = 500) -> str:
    """
    按句子边界截断文本，避免在词或标点中间断开。
    """
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    sentence_endings = re.compile(r'[。．.！!？?\n]')

    # 查找最后一个句子结束符的位置
    match = None
    for m in sentence_endings.finditer(truncated):
        match = m

    # 动态最小保留长度：至少保留 max_chars 的 60%，但不少于 50 字符
    min_keep = max(int(max_chars * 0.6), 50)

    if match and match.end() >= min_keep:
        return truncated[:match.end()] + "... [truncated]"

    # 如果没有合适的句子结束符，尝试按空格截断（英文）
    last_space = truncated.rfind(' ')
    if last_space != -1 and last_space >= min_keep:
        return truncated[:last_space] + "... [truncated]"

    # 极端情况：硬截断并加标记
    return truncated + "... [truncated]"


def _extract_content(response) -> Optional[str]:
    """安全提取 API 响应中的文本内容"""
    try:
        message = response.choices[0].message
        print('def _extract_content message : {}'.format(message))
        content = getattr(message, "content", None)
        print('def _extract_content content : {}'.format(content))
        return content.strip() if content else None
    except (AttributeError, IndexError):
        return None


def compress_text_v1(
    text: str,
    max_words: int = 150,
    role: str = "financial news",
    config: Optional[dict] = None,
    max_retries: int = 2,        # API 异常时的重试次数
    max_revisions: int = 1,      # 字数超标时的修正次数
) -> str:
    """
    调用压缩 API 压缩文本。
    采用两段式策略：
      1. API 请求阶段：网络/服务异常时自动重试 max_retries 次
      2. 内容修正阶段：字数超标时请求 LLM 重写，最多 max_revisions 次
    若全部失败，降级为本地 safe_truncate。
    """
    # ---- 前置检查 ----
    if not text or len(text) < 100:
        return text

    if config is None:
        config = get_compress_config()

    # fallback_chars = max(int(max_words * 4), 100)
    fallback_chars = max(int(max_words), 100)
    client = _get_client(config)
    max_tokens = int(max_words * TOKEN_PER_WORD) + 20
    threshold = int(max_words * 1.15)

    # ---- 原始 prompt（使用 role 参数）----
    prompt = f"""You are a senior financial analyst. Provide a concise summary of the following {role} text.
Your summary must:
- Capture all major announcements, data releases, or material events.
- Clearly state the overall sentiment (bullish/bearish/neutral) with a brief justification.
- Explain the direct implications for the company or market.
- Be concise, aiming for approximately {max_words} words. You may exceed by up to 15%, but avoid unnecessary verbosity.
Output only the summary, without any introductory phrases.

Text to summarize:
{text}"""

    # ============================================================
    # 第 1 阶段：原始请求（含 API 异常重试）
    # ============================================================
    compressed = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": "You are an expert summarizer of financial news."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            # response : ChatCompletion(id='chatcmpl-894a4c68c160112b', choices=[Choice(finish_reason='length', index=0, logprobs=None, message=ChatCompletionMessage(content=None, refusal=None, role='assistant', annotations=None, audio=None, function_call=None, tool_calls=[], reasoning="Here's a thinking process:\n\n1.  **Analyze User Input:**\n   - **Role:** Senior financial analyst\n   - **Task:** Summarize stock price data for AAPL (July 23, 2026 - August 21, 2026)\n   - **Requirements:**\n     - Capture all major announcements, data releases, or material events.\n     - Clearly state overall sentiment (bullish/bearish/neutral) with brief justification.\n     - Explain direct implications for the company or market.\n     - Concise, ~60 words (up to 15% over = ~69 words max"), stop_reason=None, token_ids=None)], created=1788089844, model='qwen3.6-27B', object='chat.completion', moderation=None, service_tier=None, system_fingerprint=None, usage=CompletionUsage(completion_tokens=140, prompt_tokens=1454, total_tokens=1594, completion_tokens_details=None, prompt_tokens_details=None), prompt_logprobs=None, prompt_token_ids=None, kv_transfer_params=None)
            compressed = _extract_content(response)
            # compressed : None
            break  # API 调用成功（无论内容是否为空），跳出重试循环
        except Exception as e:
            print(f"   ⚠️ Compression API attempt {attempt+1}/{max_retries+1} failed: {e}")
            if attempt == max_retries:
                return safe_truncate(text, max_chars=fallback_chars)
            # 否则继续下一轮 API 重试

    if compressed is None:
        return safe_truncate(text, max_chars=fallback_chars)

    word_count = estimate_word_count(compressed)
    if word_count <= threshold:
        return compressed

    # ============================================================
    # 第 2 阶段：字数修正（最多 max_revisions 次）
    # ============================================================
    for revision in range(max_revisions):
        try:
            retry_msg = (
                f"Your previous summary was {word_count} words, exceeding the {max_words} word limit. "
                f"Please rewrite the following summary to be strictly within {max_words} words:\n\n{compressed}"
            )
            response = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": "You are an expert summarizer. Follow word limits strictly."},
                    {"role": "user", "content": retry_msg}
                ],
                max_tokens=max_tokens,
                temperature=0.2,
            )
            compressed = _extract_content(response)
            if compressed is None:
                # 修正时 API 返回空内容，直接回退到原文截断
                return safe_truncate(text, max_chars=fallback_chars)
            word_count = estimate_word_count(compressed)
            if word_count <= threshold:
                return compressed
        except Exception as e:
            print(f"   ⚠️ Compression revision {revision+1}/{max_revisions} failed: {e}")
            break  # 修正时 API 异常，不再继续修正，直接走最终截断

    # ============================================================
    # 最终降级：本地截断
    # ============================================================
    if word_count > threshold:
        compressed = safe_truncate(compressed, max_chars=fallback_chars)

    return compressed


def compress_text(
    text: str,
    max_words: int = 150,
    role: str = "financial news",
    config: Optional[dict] = None,
    max_retries: int = 2,
    max_revisions: int = 1,
) -> str:
    """
    对长文本进行智能摘要和关键信息提取。
    保留接口参数，但内部逻辑改为：提取核心事件、总体情绪、潜在影响。
    """
    # ---- 前置检查 ----
    if not text or len(text) < 100:
        return text

    if config is None:
        config = get_compress_config()

    # 设定合理的 token 上限（不再受 max_words 的严格限制）
    max_tokens = max(5000, int(max_words * TOKEN_PER_WORD) + 3000)
    print(f'>>> compress_text max_tokens: {max_tokens}')

    client = _get_client(config)

    # ---- 改进后的提示词：要求结构化摘要 ----
    prompt = f"""
You are a senior financial analyst. Extract the key insights from the following {role} text.

Your summary MUST include:
1. **Key Event(s):** The most important news or data releases mentioned.
2. **Overall Sentiment:** Bullish / Bearish / Neutral, with a one‑sentence justification.
3. **Market Impact:** What this means for the company or the broader market.

Be concise and factual. Aim for approximately {max_words} words, but do not sacrifice clarity for brevity.
Output only the summary, without any reasoning, analysis, or thinking process.

Text to summarize:
{text}
"""

    # ============================================================
    # 第 1 阶段：原始请求（含 API 异常重试）
    # ============================================================
    compressed = None
    for attempt in range(max_retries + 1):
        try:
            print('-0-' * 10)
            response = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": "You are an expert summarizer of financial news. Extract key points only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            # 尝试从 content 提取
            print('000 response : {}'.format(response))
            compressed = _extract_content(response)
            print('000 compressed : {}'.format(compressed))
            # 如果 content 为空，尝试从 reasoning 字段提取（若存在）
            if compressed is None:
                reasoning = getattr(response.choices[0].message, "reasoning", None)
                if reasoning:
                    # 简单提取：取 reasoning 的最后一段（通常包含结论）
                    parts = reasoning.strip().split("\n\n")
                    if parts:
                        compressed = parts[-1].strip()
            break
        except Exception as e:
            print(f"   ⚠️ Compression API attempt {attempt+1}/{max_retries+1} failed: {e}")
            if attempt == max_retries:
                # 最终降级：返回原文本的安全截断
                return safe_truncate(text, max_chars=max_words * 4 if max_words else 500)
            continue

    # 如果仍然为空，返回原文本的安全截断
    if not compressed:
        print('⚠️ compress_text: No summary generated, falling back to safe_truncate')
        return safe_truncate(text, max_chars=max_words * 4 if max_words else 500)

    # ---- 可选：字数修正（保留但简化，因为 prompt 已引导接近目标词数） ----
    word_count = estimate_word_count(compressed)
    print('111 word_count : {}'.format(word_count))
    threshold = int(max_words * 1.5)  # 放宽阈值，避免频繁修正
    print('111 threshold : {}'.format(threshold))
    if word_count > threshold:
        print('-2-' * 10)
        # 尝试一次修正
        try:
            retry_prompt = f"Please rewrite the following summary to be more concise, within approximately {max_words} words:\n\n{compressed}"
            response = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": "You are an expert summarizer. Shorten the text while keeping key points."},
                    {"role": "user", "content": retry_prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.2,
            )
            compressed_new = _extract_content(response)
            if compressed_new:
                compressed = compressed_new
        except Exception as e:
            print(f"   ⚠️ Compression revision failed: {e}")

    return compressed