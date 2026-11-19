"""Flask 入口与路由。"""

from __future__ import annotations

import logging
import random
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

import config
from core.parser import ParseError, parse_text
from core.pdf_builder import RenderOptions, build_pdf, register_fonts
from core.pinyin_gen import build_words

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
app.json.ensure_ascii = False
app.logger.setLevel(logging.INFO)

# 启动时注册字体，避免每请求重复加载
register_fonts()


# ------------------------------------------------------------------ 工具
def _now_shanghai() -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Shanghai"))
    except Exception:  # pragma: no cover - 无 tzdata 时回退
        return datetime.now()


def _clamp_float(value, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or number in (float("inf"), float("-inf")):
        return default
    return max(low, min(high, number))


def _as_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def _build_options(data: dict) -> RenderOptions:
    paper = str(data.get("paper", "A4")).strip().upper()
    if paper not in config.LAYOUT_PRESETS:
        raise ParseError("纸张类型只能是 A4 或 A5")

    preset = config.LAYOUT_PRESETS[paper]
    low, high = config.GRID_SIZE_RANGE
    grid_size = _clamp_float(data.get("grid_size"), preset["grid_size"], low, high)
    low, high = config.PINYIN_SIZE_RANGE
    pinyin_size = _clamp_float(
        data.get("pinyin_font_size"), preset["pinyin_font_size"], low, high
    )

    return RenderOptions(
        paper=paper,
        grid_size=grid_size,
        pinyin_font_size=pinyin_size,
        show_header=_as_bool(data.get("show_header"), True),
        show_answer=_as_bool(data.get("show_answer"), False),
        show_page_number=_as_bool(data.get("show_page_number"), False),
        draw_diagonals=_as_bool(data.get("draw_diagonals"), False),
    )


def _make_filename(paper: str) -> str:
    return f"看拼音写词语_{paper}_{_now_shanghai():%Y%m%d_%H%M}.pdf"


def _prepare_words(raw: str, shuffle: bool):
    specs = parse_text(raw)
    words, warnings = build_words(specs)
    if not words:
        raise ParseError("没有可用的词语，请检查输入内容")
    if shuffle:
        random.shuffle(words)
    return words, warnings


# ------------------------------------------------------------------ 路由
@app.get("/")
def index():
    return render_template("index.html")


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.post("/api/parse")
def api_parse():
    try:
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            raise ParseError("请求格式错误，应为 JSON")
        words, warnings = _prepare_words(str(data.get("words", "")), False)
        return jsonify(
            {
                "count": len(words),
                "char_count": sum(len(word.text) for word in words),
                "words": [
                    {"text": w.text, "pinyin": w.pinyin, "manual": w.manual}
                    for w in words
                ],
                "warnings": warnings,
            }
        )
    except ParseError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:  # pragma: no cover
        app.logger.exception("解析词语失败")
        return jsonify({"error": "解析词语时发生内部错误，请稍后重试"}), 500


@app.post("/api/pdf")
def api_pdf():
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ParseError("请求格式错误，应为 JSON")

        options = _build_options(data)
        words, _warnings = _prepare_words(
            str(data.get("words", "")), _as_bool(data.get("shuffle"), False)
        )

        buffer = build_pdf(words, options)
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=False,
            download_name=_make_filename(options.paper),
            max_age=0,
        )
    except ParseError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:  # pragma: no cover
        app.logger.exception("生成 PDF 失败")
        return jsonify({"error": "生成 PDF 时发生内部错误，请稍后重试"}), 500


# ------------------------------------------------------------------ 错误
@app.errorhandler(RequestEntityTooLarge)
def handle_too_large(_exc):
    return jsonify({"error": "提交内容过大（上限 64KB），请减少词语数量"}), 400


@app.errorhandler(HTTPException)
def handle_http_error(exc: HTTPException):
    return jsonify({"error": f"请求错误（{exc.code}）"}), exc.code


@app.errorhandler(Exception)
def handle_unexpected(exc: Exception):  # pragma: no cover
    if isinstance(exc, HTTPException):
        return handle_http_error(exc)
    app.logger.exception("未处理的异常")
    return jsonify({"error": "服务器内部错误，请稍后重试"}), 500


if __name__ == "__main__":  # 本地调试用，生产请用 gunicorn
    app.run(host="0.0.0.0", port=8000, debug=True)