"""文本解析：分隔符容错、手动拼音校验、去重、数量上限。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from config import MAX_WORDS

_SEPARATORS = re.compile(r"[\n\r，,、]+")


class ParseError(ValueError):
    """可直接展示给用户的中文错误。"""


@dataclass
class WordSpec:
    text: str
    manual_pinyin: list[str] | None = None


def parse_text(raw: str) -> list[WordSpec]:
    """把用户输入解析为 WordSpec 列表。

    规则：
      - 分隔符：换行 / 中文逗号 / 英文逗号 / 顿号 / 空格
      - 手动拼音：``词语|pīn yīn``，拼音按空格分隔，数量必须等于字数
      - 去重后按原顺序保留
    """
    specs: list[WordSpec] = []
    for segment in _SEPARATORS.split(raw or ""):
        segment = segment.strip()
        if not segment:
            continue
        if "|" in segment:
            specs.extend(_parse_manual(segment))
        else:
            specs.extend(WordSpec(part) for part in segment.split())
    return _dedupe_and_check(specs)


def _parse_manual(segment: str) -> list[WordSpec]:
    left, _, right = segment.partition("|")
    left, right = left.strip(), right.strip()

    if "|" in right:
        raise ParseError(f"「{segment}」中只能出现一个「|」")

    head = left.split()
    if not head:
        raise ParseError(f"「{segment}」的「|」左侧缺少词语")

    word = head[-1]
    if not right:
        raise ParseError(f"「{word}」的拼音为空，请写成「{word}|pīn yīn」的形式")

    syllables = right.split()
    if len(syllables) != len(word):
        raise ParseError(
            f"「{word}」有 {len(word)} 个字，但指定了 {len(syllables)} 个拼音，"
            "数量必须一致"
        )

    specs = [WordSpec(part) for part in head[:-1]]
    specs.append(WordSpec(word, syllables))
    return specs


def _dedupe_and_check(specs: list[WordSpec]) -> list[WordSpec]:
    seen: set[str] = set()
    result: list[WordSpec] = []
    for spec in specs:
        if spec.text in seen:
            continue
        seen.add(spec.text)
        result.append(spec)

    if not result:
        raise ParseError("没有解析到任何词语，请输入词语并用换行或逗号分隔")
    if len(result) > MAX_WORDS:
        raise ParseError(
            f"单次最多支持 {MAX_WORDS} 个词语，当前为 {len(result)} 个，请拆分后再试"
        )
    return result