# -*- coding: utf-8 -*-
"""取词层：把一页 PDF 变成“若干行，每行若干单元格”。

这是整个引擎里**唯一依赖 PDF 库**的模块。换库、加别的取词方式，都只动这里，
下游拿到的始终是同一个结构：

    pages = [
        {"no": 1, "rows": [[(x, "文本"), (x, "文本"), ...], ...]},
    ]

为什么不用 pdfium 自带的换行
---------------------------
pdfium 判断“列间距过大”就插换行，对这些宽表是灾难：新华一页 71 行会被拆成 184 行。
所以这里按字符坐标自己重建：同一基线归一行，行内按水平间距切字段。
另外字符框（get_charbox）对 `一`、`+` 这类笔画稀疏的字会偏低，基线改用字符原点。
"""

from __future__ import annotations

import ctypes
import hashlib
import sys
from pathlib import Path

try:
    import pypdfium2 as pdfium
    import pypdfium2.raw as pdfium_raw
except ImportError:  # pragma: no cover
    sys.exit("缺少依赖：请先执行  python -m pip install pypdfium2")

from engine.spec import Spec


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_row(row: list, cell_gap: float) -> list:
    """把同一基线的字符按 x 排序，间距大的地方切开成字段。返回 [(x, 文本), ...]。"""
    row.sort(key=lambda item: item[1])
    cells = []
    current = row[0][0]
    start = row[0][1]
    prev_right = row[0][3]
    for char, x0, _oy, x1 in row[1:]:
        if char.isspace():
            continue
        if x0 - prev_right > cell_gap:
            cells.append((start, current))
            current = char
            start = x0
        else:
            current += char
        prev_right = x1
    cells.append((start, current))
    return [(x, text) for x, text in cells if text.strip()]


def _char_origin(textpage, index: int) -> tuple:
    """字符原点（基线位置）。比 bbox 稳：`一` 这种只有一横的字，bbox 会偏低。"""
    x = ctypes.c_double()
    y = ctypes.c_double()
    pdfium_raw.FPDFText_GetCharOrigin(textpage.raw, index, ctypes.byref(x), ctypes.byref(y))
    return x.value, y.value


def _page_rows(page, spec: Spec) -> list:
    """一页 → 若干行，每行是 [(x, 文本), ...]。"""
    textpage = page.get_textpage()
    chars = []
    try:
        for index in range(textpage.count_chars()):
            char = textpage.get_text_range(index, 1)
            if not char or char in "\r\n\t":
                continue
            x0, _y0, x1, _y1 = textpage.get_charbox(index)
            _ox, origin_y = _char_origin(textpage, index)
            chars.append((char, x0, origin_y, x1))
    finally:
        textpage.close()
        page.close()

    chars.sort(key=lambda item: (-item[2], item[1]))
    rows = []
    current = []
    baseline = None
    for item in chars:
        if baseline is None or abs(item[2] - baseline) <= spec.row_gap:
            current.append(item)
            if baseline is None:
                baseline = item[2]
        else:
            rows.append(_render_row(current, spec.cell_gap))
            current = [item]
            baseline = item[2]
    if current:
        rows.append(_render_row(current, spec.cell_gap))
    return [row for row in rows if row]


def read_pages(pdf_path: Path, spec: Spec) -> tuple:
    """取出需要解析的页。返回 (页列表, 总页数)；页里的 rows 是 [(x, 文本), ...]。"""
    pages = []
    with pdfium.PdfDocument(str(pdf_path)) as doc:
        total = len(doc)
        for no in range(1, total + 1):
            if spec.pages is not None and no not in spec.pages:
                continue
            pages.append({"no": no, "rows": _page_rows(doc[no - 1], spec)})
    return pages, total
