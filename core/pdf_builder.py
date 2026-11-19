"""组装页面：逐页逐行逐格绘制田字格、拼音、标题栏与答案页。"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import config
from .grid import draw_grid
from .layout import Layout, Page, build_layout
from .pinyin_gen import Word

TEXT_COLOR = HexColor("#333333")
MUTED_COLOR = HexColor("#666666")
ANSWER_COLOR = HexColor("#222222")

# 拼音基线相对田字格顶边的偏移（mm）
PINYIN_BASELINE_OFFSET = 1.2
# 拼音宽度超过格子宽度的比例上限，超出则按比例缩小字号
PINYIN_MAX_WIDTH_RATIO = 0.96
PINYIN_MIN_FONT_SIZE = 5.0

HEADER_TEXT = "姓名：__________   班级：__________   日期：__________   得分：__________"

_pinyin_font = "Helvetica"
_chinese_font = "STSong-Light"
_fonts_ready = False


# ------------------------------------------------------------------ 字体
def register_fonts() -> None:
    """注册字体（应用启动时调用一次，避免每请求重复加载）。"""
    global _pinyin_font, _chinese_font, _fonts_ready
    if _fonts_ready:
        return

    if os.path.exists(config.PINYIN_FONT_PATH):
        pdfmetrics.registerFont(
            TTFont(config.PINYIN_FONT_NAME, config.PINYIN_FONT_PATH)
        )
        _pinyin_font = config.PINYIN_FONT_NAME

    if os.path.exists(config.CHINESE_FONT_PATH):
        pdfmetrics.registerFont(
            TTFont(config.CHINESE_FONT_NAME, config.CHINESE_FONT_PATH)
        )
        _chinese_font = config.CHINESE_FONT_NAME
    else:  # 兜底：ReportLab 内置 CJK 字体，保证不崩溃
        try:
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        except Exception:  # pragma: no cover
            pass
        _chinese_font = "STSong-Light"

    _fonts_ready = True


def pinyin_font_name() -> str:
    return _pinyin_font


def chinese_font_name() -> str:
    return _chinese_font


# ------------------------------------------------------------------ 选项
@dataclass
class RenderOptions:
    paper: str = "A4"
    grid_size: float = 16.0
    pinyin_font_size: float = 10.0
    show_header: bool = True
    show_answer: bool = False
    show_page_number: bool = False
    draw_diagonals: bool = False


# ------------------------------------------------------------------ 入口
def build_pdf(words: list[Word], options: RenderOptions) -> io.BytesIO:
    """生成 PDF，返回定位到 0 的 BytesIO。"""
    register_fonts()

    preset = config.get_preset(options.paper)
    layout = build_layout(words, preset, options.grid_size, options.show_header)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(
        buffer,
        pagesize=(preset["page_w"] * mm, preset["page_h"] * mm),
    )
    pdf.setTitle("看拼音写词语")
    pdf.setAuthor("看拼音写词语")
    pdf.setSubject(f"看拼音写词语练习卷（{options.paper}）")

    total_pages = len(layout.pages) * (2 if options.show_answer else 1)
    page_no = 0

    for page in layout.pages:
        page_no += 1
        _draw_page(pdf, page, preset, layout, options,
                   answer=False, page_no=page_no, total_pages=total_pages)
        pdf.showPage()

        if options.show_answer:
            page_no += 1
            _draw_page(pdf, page, preset, layout, options,
                       answer=True, page_no=page_no, total_pages=total_pages)
            pdf.showPage()

    pdf.save()
    buffer.seek(0)
    return buffer


# ------------------------------------------------------------------ 页面
def _draw_page(
    pdf: canvas.Canvas,
    page: Page,
    preset: dict[str, float],
    layout: Layout,
    options: RenderOptions,
    *,
    answer: bool,
    page_no: int,
    total_pages: int,
) -> None:
    left = preset["margin_left"]
    top = preset["page_h"] - preset["margin_top"]

    if options.show_header:
        _draw_header(pdf, left, top, preset, answer)
        top -= preset["header_h"]

    cell_top = top - preset["pinyin_area_h"]
    word_gap = preset["word_gap"]

    for row in page.rows:
        x = left
        for word, cell in zip(row.words, row.cell_sizes):
            for index, char in enumerate(word.text):
                cell_x = x + index * cell
                cell_y = cell_top - cell

                draw_grid(pdf, cell_x, cell_y, cell, options.draw_diagonals)
                _draw_pinyin(
                    pdf,
                    word.pinyin[index],
                    cell_x + cell / 2.0,
                    cell_y + cell + PINYIN_BASELINE_OFFSET,
                    cell,
                    options.pinyin_font_size,
                )
                if answer:
                    _draw_answer_char(
                        pdf, char, cell_x + cell / 2.0, cell_y + cell / 2.0, cell
                    )

            x += len(word.text) * cell + word_gap

        cell_top -= layout.row_h

    if options.show_page_number:
        _draw_page_number(pdf, preset, page_no, total_pages)


def _draw_header(
    pdf: canvas.Canvas,
    left: float,
    top: float,
    preset: dict[str, float],
    answer: bool,
) -> None:
    font_size = preset["header_font_size"]
    baseline = top - preset["header_h"] * 0.72

    pdf.setFont(_chinese_font, font_size)
    pdf.setFillColor(TEXT_COLOR)
    pdf.drawString(left * mm, baseline * mm, HEADER_TEXT)

    if answer:
        pdf.setFont(_chinese_font, font_size)
        pdf.setFillColor(MUTED_COLOR)
        pdf.drawRightString(
            (left + preset["content_w"]) * mm, baseline * mm, "（答案页）"
        )


def _draw_page_number(
    pdf: canvas.Canvas,
    preset: dict[str, float],
    page_no: int,
    total_pages: int,
) -> None:
    pdf.setFont(_chinese_font, preset["page_number_font_size"])
    pdf.setFillColor(MUTED_COLOR)
    pdf.drawCentredString(
        preset["page_w"] * mm / 2.0,
        preset["margin_bottom"] * 0.45 * mm,
        f"第 {page_no} 页 / 共 {total_pages} 页",
    )


# ------------------------------------------------------------------ 元素
def _draw_pinyin(
    pdf: canvas.Canvas,
    text: str,
    center_x_mm: float,
    baseline_mm: float,
    cell_mm: float,
    font_size: float,
) -> None:
    """在田字格正上方水平居中绘制一个音节。"""
    if not text:
        return

    size = float(font_size)
    max_width = cell_mm * mm * PINYIN_MAX_WIDTH_RATIO
    width = pdfmetrics.stringWidth(text, _pinyin_font, size)
    if width > max_width > 0:
        size = max(PINYIN_MIN_FONT_SIZE, size * max_width / width)

    pdf.setFont(_pinyin_font, size)
    pdf.setFillColor(TEXT_COLOR)
    pdf.drawCentredString(center_x_mm * mm, baseline_mm * mm, text)


def _draw_answer_char(
    pdf: canvas.Canvas,
    char: str,
    center_x_mm: float,
    center_y_mm: float,
    cell_mm: float,
) -> None:
    """答案页：在田字格正中用楷体填入一个汉字。"""
    size = cell_mm * mm * 0.66
    pdf.setFont(_chinese_font, size)
    pdf.setFillColor(ANSWER_COLOR)
    pdf.drawCentredString(
        center_x_mm * mm,
        center_y_mm * mm - 0.34 * size,
        char,
    )