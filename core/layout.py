"""贪心换行 + 分页（纯计算，不涉及任何绘图）。"""

from __future__ import annotations

from dataclasses import dataclass, field

import config
from .pinyin_gen import Word

_EPS = 1e-9


@dataclass
class Row:
    words: list[Word]
    cell_sizes: list[float]        # 每个词实际使用的田字格边长（mm）
    width: float                   # 该行占用宽度（mm，不含行尾留白）


@dataclass
class Page:
    rows: list[Row]


@dataclass
class Layout:
    pages: list[Page]
    row_h: float
    rows_per_page: int
    warnings: list[str] = field(default_factory=list)


def build_layout(
    words: list[Word],
    preset: dict[str, float],
    grid_size: float,
    show_header: bool,
) -> Layout:
    content_w = preset["content_w"]
    gap = preset["word_gap"]
    warnings: list[str] = []

    rows: list[Row] = []
    cur_words: list[Word] = []
    cur_cells: list[float] = []
    cur_w = 0.0

    def flush() -> None:
        nonlocal cur_words, cur_cells, cur_w
        if cur_words:
            rows.append(Row(cur_words, cur_cells, cur_w))
        cur_words, cur_cells, cur_w = [], [], 0.0

    for word in words:
        length = len(word.text)
        if length == 0:
            continue

        # 单行放不下的超长词：缩格子；缩到下限仍放不下则跳过
        cell = grid_size
        if length * cell > content_w + _EPS:
            cell = content_w / length
            if cell < config.MIN_CELL_MM:
                warnings.append(
                    f"「{word.text}」字数过多，一行内无法排下，已跳过"
                )
                continue
            warnings.append(
                f"「{word.text}」字数较多，该词田字格已缩小至 {cell:.1f}mm"
            )

        width = length * cell
        is_long = length > config.LONG_WORD_THRESHOLD
        prev_is_long = bool(cur_words) and (
            len(cur_words[-1].text) > config.LONG_WORD_THRESHOLD
        )

        need_break = bool(cur_words) and (
            cur_w + gap + width > content_w + _EPS or is_long or prev_is_long
        )
        if need_break:
            flush()

        if cur_words:
            cur_w += gap
        cur_words.append(word)
        cur_cells.append(cell)
        cur_w += width

    flush()

    row_h = config.row_height(preset, grid_size)
    per_page = config.rows_per_page(preset, grid_size, show_header)
    pages = [Page(rows[i:i + per_page]) for i in range(0, len(rows), per_page)]

    return Layout(pages=pages, row_h=row_h, rows_per_page=per_page, warnings=warnings)