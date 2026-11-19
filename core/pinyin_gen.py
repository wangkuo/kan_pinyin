"""pypinyin 封装与容错：整词取音、非中文字符标记、多音字提示。

注意：lazy_pinyin() 没有 heteronym 参数，多音字由整词上下文自动消解，
      其默认行为等价于 heteronym=False。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pypinyin import Style, lazy_pinyin, pinyin

from .parser import WordSpec

UNKNOWN_PINYIN = "？"
MAX_WARNINGS = 12


@dataclass
class Word:
    text: str
    pinyin: list[str]
    manual: bool = False


def is_cjk(ch: str) -> bool:
    """用 codepoint 判断汉字，比正则更可靠也更快。"""
    if not ch:
        return False
    code = ord(ch)
    return (
        0x3400 <= code <= 0x4DBF          # 扩展 A
        or 0x4E00 <= code <= 0x9FFF       # 基本汉字
        or 0xF900 <= code <= 0xFAFF       # 兼容汉字
        or code == 0x3007                 # 〇
    )


@lru_cache(maxsize=8192)
def _reading_count(ch: str) -> int:
    """单字读音数量（>1 即为多音字）。带缓存。"""
    try:
        result = pinyin(ch, style=Style.TONE, heteronym=True)
    except Exception:
        return 1
    if not result or not result[0]:
        return 1
    return len(set(result[0]))


def _safe_lazy_pinyin(text: str) -> list[str] | None:
    """整词取音（借助词组上下文处理多音字）。失败返回 None。"""
    try:
        # lazy_pinyin 没有 heteronym 参数；默认即只取一个读音
        result = lazy_pinyin(text, style=Style.TONE)
        return list(result) if result else None
    except Exception:
        return None


def _safe_char_pinyin(ch: str) -> str | None:
    """逐字取音，作为整词取音失败时的降级路径。"""
    try:
        result = pinyin(ch, style=Style.TONE, heteronym=False)
    except Exception:
        return None
    if not result or not result[0]:
        return None
    return result[0][0]


def build_words(specs: list[WordSpec]) -> tuple[list[Word], list[str]]:
    """把 WordSpec 转成 Word 列表，并返回用户可见的提示信息。"""
    words: list[Word] = []
    warnings: list[str] = []
    heteronym_chars: list[str] = []
    seen_heteronym: set[str] = set()

    for spec in specs:
        text = spec.text

        # 手动指定拼音：直接采用（数量已在校验阶段确认）
        if spec.manual_pinyin is not None:
            words.append(Word(text, list(spec.manual_pinyin), True))
            continue

        if not any(is_cjk(ch) for ch in text):
            warnings.append(f"「{text}」不含中文字符，已跳过")
            continue

        # 优先整词取音（多音字更准），失败则降级为逐字
        syllables = _safe_lazy_pinyin(text)
        if syllables is None or len(syllables) != len(text):
            fallback = [_safe_char_pinyin(ch) or UNKNOWN_PINYIN for ch in text]
            if all(s == UNKNOWN_PINYIN for s in fallback):
                warnings.append(f"「{text}」拼音生成失败，已跳过")
                continue
            syllables = fallback
            warnings.append(f"「{text}」整词取音异常，已降级为逐字取音")

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