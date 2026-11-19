from core.parser import parse_text
from core.pdf_builder import RenderOptions, build_pdf
from core.pinyin_gen import build_words


def render(raw, **kwargs):
    words, _warnings = build_words(parse_text(raw))
    options = RenderOptions(**kwargs)
    return build_pdf(words, options).getvalue()


def test_pdf_header_and_footer():
    data = render("春天\n花朵|huā duǒ\n小桥")
    assert data.startswith(b"%PDF")
    assert data.rstrip().endswith(b"%%EOF")
    assert len(data) > 1000


def test_pdf_a4_and_a5():
    for paper in ("A4", "A5"):
        data = render("春天\n花朵\n小桥\n流水", paper=paper)
        assert data.startswith(b"%PDF")
        assert b"/MediaBox" in data


def test_pdf_with_answer_page_is_larger():
    plain = render("春天\n花朵", show_answer=False)
    with_answer = render("春天\n花朵", show_answer=True)
    assert len(with_answer) > len(plain)


def test_pdf_handles_polyphonic_word():
    """「长大」应生成 zhǎng dà 而不是 cháng dà。"""
    words, _ = build_words(parse_text("长大"))
    assert words[0].pinyin == ["zhǎng", "dà"]


def test_non_chinese_word_is_skipped():
    words, warnings = build_words(parse_text("春天\nàí"))
    assert [w.text for w in words] == ["春天"]
    assert any("àí" in w for w in warnings)