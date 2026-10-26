# valueagents/agents/utils/compress_utils.py

import os
import re
from typing import Optional
from openai import OpenAI

# 诊断阈值：completion_tokens 超过这个值就 dump
DIAGNOSTIC_TOKEN_THRESHOLD = 2048
DIAGNOSTIC_LOG_FILE = "compress_reasoning_dump.log"

# 估算平均 token/word 比率（英文约 1.3，中文约 1.8，这里采用保守值 2.0）
TOKEN_PER_WORD = 2.0

# 模块级单例客户端缓存
_client_cache = {}

def get_compress_config_83():
    """从环境变量读取压缩服务配置"""
    return {
        "base_url": os.environ.get("COMPRESS_API_URL", ""),
        "model": os.environ.get("COMPRESS_MODEL", "qwen3_32B"),
        "api_key": os.environ.get("COMPRESS_API_KEY", "EMPTY"),
        "timeout": int(os.environ.get("COMPRESS_TIMEOUT", "3600")),
    }

def get_compress_config_75():
    """从环境变量读取压缩服务配置"""
    return {
        "base_url": os.environ.get("COMPRESS_API_URL", ""),
        "model": os.environ.get("COMPRESS_MODEL", "qwen3.6-27B"),
        "api_key": os.environ.get("COMPRESS_API_KEY", "EMPTY"),
        "timeout": int(os.environ.get("COMPRESS_TIMEOUT", "30")),
    }

def get_compress_config():
    """从环境变量读取压缩服务配置"""
    return {
        "base_url": os.environ.get("COMPRESS_API_URL", ""),
        "model": os.environ.get("COMPRESS_MODEL", "qwen3_37"),
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
        # print('def _extract_content message : {}'.format(message))
        content = getattr(message, "content", None)
        # print('def _extract_content content : {}'.format(content))
        return content.strip() if content else None
    except (AttributeError, IndexError):
        return None


def compress_text(
    text: str,
    max_words: int = 150,
    role: str = "financial news",
    config: Optional[dict] = None,
    max_retries: int = 2,
) -> str:
    """
    金融场景的两阶段压缩：
      阶段 1：LLM reasoning 提取关键信息（结构化笔记）
      阶段 2：LLM 基于笔记写成短摘要
    """
    if not text or len(text) < 100:
        return text

    if config is None:
        config = get_compress_config()

    client = _get_client(config)

    extraction_prompt = f"""Compress the following {role} text.
    
Keep it concise: clearly shorter than the input, a few short paragraphs at most.
- If input is longer, output must be SHORTER than input.
- If input is already short, output an even shorter compressed version.

Keep: key facts, core view, key numbers, dates.
Drop: redundancy, boilerplate, marketing language.

Do NOT add any overall sentiment, conclusion, or judgment.
Do NOT write an analysis report.
Do NOT write section headers like "Key Facts & Events".
Do NOT restate input.
Do NOT count words. Do NOT verify your output against these rules.
Output ONLY the compressed text.

Text:
{text}"""

    extraction = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": "You are a senior financial analyst."},
                    {"role": "user", "content": extraction_prompt},
                ],
                max_tokens=8192,
                temperature=0.1,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )

            # ===== 新增：阶段 1 验证 =====
            msg = resp.choices[0].message
            # print(f"[STAGE1] reasoning type: {type(getattr(msg, 'reasoning', None))}, "
            #     f"reasoning_len: {len(getattr(msg, 'reasoning', '') or '')}, "
            #     f"content_len: {len(getattr(msg, 'content', '') or '')}, "
            #     f"finish_reason: {resp.choices[0].finish_reason}")
            # ============================
            # print('STAGE1 input text : {}'.format(text))
            # print('STAGE1 reasoning : {}'.format(getattr(msg, 'reasoning', '')))
            # print('STAGE1 content : {}'.format(getattr(msg, 'content', '')))


            # ============================================================
            # 🔍 诊断：completion_tokens 超阈值时 dump
            # ============================================================
            try:
                usage = getattr(resp, "usage", None)
                comp_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
                finish_reason = resp.choices[0].finish_reason if resp.choices else "?"
                msg = resp.choices[0].message if resp.choices else None
                raw_content = getattr(msg, "content", None)
                raw_reasoning = getattr(msg, "reasoning", None)

                if comp_tokens >= DIAGNOSTIC_TOKEN_THRESHOLD:
                    dump = (
                        f"\n{'='*80}\n"
                        f"[DIAGNOSTIC] attempt={attempt+1} "
                        f"completion_tokens={comp_tokens} "
                        f"finish_reason={finish_reason}\n"
                        f"prompt_tokens={getattr(usage, 'prompt_tokens', '?')}\n"
                        f"input_chars={len(text)}  input_words~={len(text)//5}\n"
                        f"content_len={len(raw_content) if raw_content else 0}\n"
                        f"reasoning_len={len(raw_reasoning) if raw_reasoning else 0}\n"
                        f"{'-'*80}\n"
                        f"[CONTENT]\n{raw_content}\n"
                        f"{'-'*80}\n"
                        f"[REASONING]\n{raw_reasoning}\n"
                        f"{'='*80}\n"
                    )
                    # 写文件（完整版，方便查阅）
                    with open(DIAGNOSTIC_LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(dump)
                    # 终端打印（截断版，避免刷屏）
                    print(
                        f"\n🔍 [DIAGNOSTIC] tokens={comp_tokens} "
                        f"finish={finish_reason} "
                        f"content_len={len(raw_content) if raw_content else 0} "
                        f"reasoning_len={len(raw_reasoning) if raw_reasoning else 0}"
                    )
                    if raw_reasoning:
                        preview = raw_reasoning[:500].replace("\n", " ")
                        print(f"   reasoning preview: {preview}...")
                    print(f"   full dump → {DIAGNOSTIC_LOG_FILE}\n")
            except Exception as diag_err:
                print(f"[DIAGNOSTIC] failed to dump: {diag_err}")
            # ============================================================



            extraction = _extract_content(resp)
            if extraction is None:
                # Qwen 的 reasoning 字段兜底
                reasoning = getattr(resp.choices[0].message, "reasoning", None)
                if reasoning:
                    extraction = reasoning
            if extraction:
                break
        except Exception as e:
            print(f"   ⚠️ Extraction attempt {attempt+1} failed: {e}")
            if attempt == max_retries:
                return safe_truncate(text, max_chars=max_words * 4)

    if not extraction:
        return safe_truncate(text, max_chars=max_words * 4)

    # ============================================================
    # 阶段 2：压缩 / 成文（输入已聚焦，max_tokens 按目标长度）
    # ============================================================
    summary_prompt = f"""Based on the following extracted notes from a {role} text, write a concise summary.

Requirements:
- Approximately {max_words} words.
- Preserve ALL specific numbers (revenue, growth rates, price targets, percentages, dates).
- State the overall sentiment in ONE sentence with a brief justification.
- Professional financial analyst tone.
- Output ONLY the summary, no preamble, no reasoning.

Extracted notes:
{extraction}"""

    # 阶段 2 的 max_tokens 按目标词数严格控制
    summary_max_tokens = int(max_words * 2) + 500
    # print('阶段2 --- summary_max_tokens : {}'.format(summary_max_tokens))

    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": "You are a senior financial analyst. /no_think"},
                    {"role": "user", "content": summary_prompt},
                ],
                max_tokens=summary_max_tokens,
                temperature=0.1,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )


            # ===== 新增：阶段 2 验证 =====
            msg = resp.choices[0].message
            # print(f"[STAGE2] reasoning type: {type(getattr(msg, 'reasoning', None))}, "
            #     f"reasoning_len: {len(getattr(msg, 'reasoning', '') or '')}, "
            #     f"content_len: {len(getattr(msg, 'content', '') or '')}, "
            #     f"finish_reason: {resp.choices[0].finish_reason}")
            # ============================
            # print('STAGE2 input text : {}'.format(extraction))
            # print('STAGE2 reasoning : {}'.format(getattr(msg, 'reasoning', '')))
            # print('STAGE2 content : {}'.format(getattr(msg, 'content', '')))


            summary = _extract_content(resp)
            if summary is None:
                # 如果阶段 2 还是走了 reasoning，取最后一段作为摘要
                reasoning = getattr(resp.choices[0].message, "reasoning", None)
                if reasoning:
                    summary = reasoning.strip().split("\n\n")[-1].strip()
            if summary:
                return summary
        except Exception as e:
            print(f"   ⚠️ Summary attempt {attempt+1} failed: {e}")

    # 全部失败，本地兜底
    return safe_truncate(text, max_chars=max_words * 4)