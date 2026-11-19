"""集中配置：排版预设、字体路径、上限常量。

所有排版数值集中在此，绘图逻辑中禁止硬编码。
"""

from __future__ import annotations

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")

# ---------------------------------------------------------------- 字体
PINYIN_FONT_PATH = os.path.join(FONT_DIR, "DejaVuSans.ttf")
CHINESE_FONT_PATH = os.path.join(FONT_DIR, "LXGWWenKai-Regular.ttf")

PINYIN_FONT_NAME = "DejaVuSans"
CHINESE_FONT_NAME = "LXGWWenKai"

# ---------------------------------------------------------------- 上限
MAX_WORDS = 200
MAX_CONTENT_LENGTH = 64 * 1024          # 64KB

GRID_SIZE_RANGE = (13.0, 22.0)          # mm
PINYIN_SIZE_RANGE = (9.0, 14.0)         # pt

# 单词过长时允许的最小格边长，低于此值直接跳过该词
MIN_CELL_MM = 9.0
# 超过该字数的词语独占一行
LONG_WORD_THRESHOLD = 4

# ---------------------------------------------------------------- 排版预设
LAYOUT_PRESETS: dict[str, dict[str, float]] = {
    "A4": {
        "page_w": 210.0,
        "page_h": 297.0,
        "margin_left": 15.0,
        "margin_right": 15.0,
        "margin_top": 15.0,
        "margin_bottom": 15.0,
        "content_w": 180.0,
        "grid_size": 16.0,
        "word_gap": 10.0,
        "pinyin_font_size": 10.0,
        "pinyin_area_h": 6.0,
        "row_gap": 8.0,
        "header_h": 12.0,
        "header_font_size": 10.0,
        "page_number_font_size": 9.0,
    },
    "A5": {
        "page_w": 148.0,
        "page_h": 210.0,
        "margin_left": 10.0,
        "margin_right": 10.0,
        "margin_top": 10.0,
        "margin_bottom": 10.0,
        "content_w": 128.0,
        "grid_size": 14.0,
        "word_gap": 8.0,
        "pinyin_font_size": 9.0,
        "pinyin_area_h": 5.0,
        "row_gap": 6.0,
        "header_h": 10.0,
        "header_font_size": 9.0,
        "page_number_font_size": 8.0,
    },
}


def get_preset(paper: str) -> dict[str, float]:
    """按纸型取排版预设，非法值回退到 A4。"""
    return LAYOUT_PRESETS.get((paper or "A4").strip().upper(), LAYOUT_PRESETS["A4"])


def row_height(preset: dict[str, float], grid_size: float) -> float:
    """行高 = 拼音区高度 + 田字格边长 + 行间距（mm）。"""
    return preset["pinyin_area_h"] + grid_size + preset["row_gap"]


def rows_per_page(preset: dict[str, float], grid_size: float, show_header: bool) -> int:
    """当前参数下一页面可容纳的行数。"""
    usable = preset["page_h"] - preset["margin_top"] - preset["margin_bottom"]
    if show_header:
        usable -= preset["header_h"]
    height = row_height(preset, grid_size)
    return max(1, int(usable // height + 1e-9))