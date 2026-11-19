"""单个田字格绘制原语。

参数均为 mm，内部转换为 pt 后交给 ReportLab。
"""

from __future__ import annotations

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm

GRID_LINE_COLOR = HexColor("#888888")
GRID_CENTER_COLOR = HexColor("#AAAAAA")

GRID_LINE_WIDTH = 0.6
GRID_CENTER_WIDTH = 0.4
GRID_CENTER_DASH = [2, 2]


def draw_grid(
    canvas,
    x_mm: float,
    y_mm: float,
    size_mm: float,
    draw_diagonals: bool = False,
) -> None:
    """在 (x_mm, y_mm) 处绘制一个边长 size_mm 的田字格（左下角为原点）。"""
    x, y, size = x_mm * mm, y_mm * mm, size_mm * mm

    canvas.saveState()

    # 外框：实线
    canvas.setLineWidth(GRID_LINE_WIDTH)
    canvas.setStrokeColor(GRID_LINE_COLOR)
    canvas.setDash([], 0)
    canvas.rect(x, y, size, size, stroke=1, fill=0)

    # 横中线 / 竖中线：虚线
    canvas.setLineWidth(GRID_CENTER_WIDTH)
    canvas.setStrokeColor(GRID_CENTER_COLOR)
    canvas.setDash(GRID_CENTER_DASH, 0)
    canvas.line(x, y + size / 2.0, x + size, y + size / 2.0)
    canvas.line(x + size / 2.0, y, x + size / 2.0, y + size)

    # 米字格对角线（默认关闭，预留开关）
    if draw_diagonals:
        canvas.line(x, y, x + size, y + size)
        canvas.line(x, y + size, x + size, y)

    canvas.restoreState()