import pytest

from config import MAX_WORDS
from core.parser import ParseError, parse_text


def texts(specs):
    return [spec.text for spec in specs]


def test_split_by_all_separators():
    specs = parse_text("春天，花朵、小桥 流水\n白云,月亮")
    assert texts(specs) == ["春天", "花朵", "小桥", "流水", "白云", "月亮"]


def test_strip_and_drop_empty_lines():
    specs = parse_text("\n\n  春天  \n\n   花朵   \n")
    assert texts(specs) == ["春天", "花朵"]


def test_dedupe_keeps_original_order():
    specs = parse_text("春天\n花朵\n春天\n白云")
    assert texts(specs) == ["春天", "花朵", "白云"]


def test_manual_pinyin_parsed():
    specs = parse_text("长大|zhǎng dà")
    assert texts(specs) == ["长大"]
    assert specs[0].manual_pinyin == ["zhǎng", "dà"]


def test_manual_pinyin_count_mismatch():
    with pytest.raises(ParseError):
        parse_text("长大|zhǎng")


def test_manual_pinyin_empty():
    with pytest.raises(ParseError):
        parse_text("长大|")


def test_manual_pinyin_after_plain_words():
    specs = parse_text("春天 长大|zhǎng dà")
    assert texts(specs) == ["春天", "长大"]
    assert specs[1].manual_pinyin == ["zhǎng", "dà"]


def test_empty_input_raises():
    with pytest.raises(ParseError):
        parse_text("   \n  ")


def test_word_limit():
    raw = "\n".join(f"词{i}" for i in range(MAX_WORDS + 1))
    with pytest.raises(ParseError):
        parse_text(raw)

    raw_ok = "\n".join(f"词{i}" for i in range(MAX_WORDS))
    assert len(parse_text(raw_ok)) == MAX_WORDS