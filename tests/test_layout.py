import config
from core.layout import build_layout
from core.pinyin_gen import Word

A4 = config.get_preset("A4")
A5 = config.get_preset("A5")


def make_word(text):
    return Word(text, ["a"] * len(text))


def make_words(texts):
    return [make_word(t) for t in texts]


def test_rows_per_page_matches_spec():
    assert config.rows_per_page(A4, 16.0, True) == 8
    assert config.rows_per_page(A5, 14.0, True) == 7


def test_row_height_matches_spec():
    assert config.row_height(A4, 16.0) == 30.0
    assert config.row_height(A5, 14.0) == 25.0


def test_one_char_words_per_row_a4():
    layout = build_layout(make_words(["春"] * 8), A4, 16.0, True)
    first_row = layout.pages[0].rows[0]
    assert len(first_row.words) == 7          # 7 × 16 + 6 × 10 = 172 ≤ 180
    assert first_row.width == 172.0


def test_two_char_words_per_row_a4():
    layout = build_layout(make_words(["春天"] * 5), A4, 16.0, True)
    assert len(layout.pages[0].rows[0].words) == 4   # 158 ≤ 180


def test_three_and_four_char_words_per_row_a4():
    layout = build_layout(make_words(["中国人"] * 4), A4, 16.0, True)
    assert len(layout.pages[0].rows[0].words) == 3   # 164 ≤ 180

    layout = build_layout(make_words(["春暖花开"] * 3), A4, 16.0, True)
    assert len(layout.pages[0].rows[0].words) == 2   # 138 ≤ 180


def test_long_word_takes_its_own_row():
    """超过 4 字的词语独占一行（已确认决策 #5）。"""
    words = make_words(["一二三四五", "春天", "花朵"])
    layout = build_layout(words, A4, 16.0, True)
    rows = layout.pages[0].rows
    assert [w.text for w in rows[0].words] == ["一二三四五"]
    assert [w.text for w in rows[1].words] == ["春天", "花朵"]


def test_word_never_split_across_rows():
    texts = ["春天", "花朵", "小桥", "流水", "白云", "月亮", "太阳"]
    layout = build_layout(make_words(texts), A4, 16.0, True)
    flat = [w.text for row in layout.pages[0].rows for w in row.words]
    assert flat == texts
    for row in layout.pages[0].rows:
        assert row.width <= A4["content_w"] + 1e-6


def test_pagination_splits_rows_not_words():
    texts = [f"词{i}" for i in range(50)]
    layout = build_layout(make_words(texts), A4, 16.0, True)

    total_rows = sum(len(page.rows) for page in layout.pages)
    assert total_rows == 13                     # 50 个 2 字词 → 每行 4 个 → 13 行
    assert len(layout.pages) == 2               # 每页 8 行 → 2 页
    assert all(len(page.rows) <= 8 for page in layout.pages)

    flat = [w.text for page in layout.pages for row in page.rows for w in row.words]
    assert flat == texts


def test_oversized_word_is_skipped_with_warning():
    words = make_words(["一" * 40])
    layout = build_layout(words, A4, 16.0, True)
    assert layout.pages == []
    assert layout.warnings