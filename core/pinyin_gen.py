"""pypinyin 封装与容错：整词取音、非中文字符标记、多音字提示。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from pypinyin import Style, lazy_pinyin, pinyin

from .parser import WordSpec

# 常用汉字区 + 扩展 A + 兼容区 + 〇
_CJK_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3007]")

UNKNOWN_PINYIN = "？"
MAX_WARNINGS = 12


@dataclass
class Word:
    text: str
    pinyin: list[str]
    manual: bool = False


def is_cjk(ch: str) -> bool:
    return bool(_CJK_RE.match(ch))


@lru_cache(maxsize=8192)
def _reading_count(ch: str) -> int:
    """单字读音数量（>1 即为多音字）。带缓存，避免重复计算。"""
    try:
        result = pinyin(ch, style=Style.TONE, heteronym=True)
    except Exception:  # pragma: no cover - 极端容错
        return 1
    if not result or not result[0]:
        return 1
    return len(set(result[0]))


def build_words(specs: list[WordSpec]) -> tuple[list[Word], list[str]]:
    """把 WordSpec 转成 Word 列表，并返回用户可见的提示信息。"""
    words: list[Word] = []
    warnings: list[str] = []
    heteronym_chars: list[str] = []
    seen_heteronym: set[str] = set()

    for spec in specs:
        text = spec.text

        # 手动指定拼音：直接采用，不做二次校验（数量已在校验阶段确认）
        if spec.manual_pinyin is not None:
            words.append(Word(text, list(spec.manual_pinyin), True))
            continue

        # 整词都非中文：跳过
        if not any(is_cjk(ch) for ch in text):
            warnings.append(f"「{text}」不含中文字符，已跳过")
            continue

        try:
            # 按整词调用，利用词组上下文处理多音字（如「长大」→ zhǎng dà）
            syllables = list(lazy_pinyin(text, style=Style.TONE, heteronym=False))
        except Exception:  # pragma: no cover - 极端容错
            warnings.append(f"「{text}」拼音生成失败，已跳过")
            continue

        if len(syllables) != len(text):
            syllables = (syllables + [UNKNOWN_PINYIN] * len(text))[: len(text)]

        cell_pinyin: list[str] = []
        for char, syllable in zip(text, syllables):
            if not is_cjk(char):
                cell_pinyin.append(UNKNOWN_PINYIN)
                warnings.append(
                    f"「{text}」中的「{char}」不是中文字符，该格拼音显示为「？」"
                )
                continue
            cell_pinyin.append(syllable or UNKNOWN_PINYIN)
            if _reading_count(char) > 1 and char not in seen_heteronym:
                seen_heteronym.add(char)
                heteronym_chars.append(f"「{char}」")

        words.append(Word(text, cell_pinyin, False))

    if heteronym_chars:
        warnings.insert(
            0,
            "多音字已按词组自动判定：" + "、".join(heteronym_chars)
            + "（如需修正请写成「词语|pīn yīn」）",
        )

    return words, _limit_warnings(warnings)


def _limit_warnings(warnings: list[str]) -> list[str]:
    if len(warnings) <= MAX_WARNINGS:
        return warnings
    hidden = len(warnings) - MAX_WARNINGS
    return warnings[:MAX_WARNINGS] + [f"……另有 {hidden} 条提示未显示"]