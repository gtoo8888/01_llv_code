# -*- coding: utf-8 -*-
"""临时原型：用 pdfium 的字符坐标重建表格行，和 pdfplumber 的行做对比。"""
import sys
import pypdfium2 as pdfium
import pdfplumber

pdf_path = sys.argv[1]
page_no = int(sys.argv[2])
row_gap = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
space_gap = float(sys.argv[4]) if len(sys.argv) > 4 else 1.6


def rows_from_pdfium(path, page_index, row_gap, space_gap):
    doc = pdfium.PdfDocument(path)
    page = doc[page_index]
    tp = page.get_textpage()
    items = []
    for i in range(tp.count_chars()):
        ch = tp.get_text_range(i, 1)
        if not ch or ch in "\r\n":
            continue
        x0, y0, x1, y1 = tp.get_charbox(i)
        items.append((ch, x0, y0, x1, y1))

    # 按基线 y（用 y0）聚类，从上往下
    items.sort(key=lambda it: (-it[2], it[1]))
    rows = []
    current = []
    baseline = None
    for it in items:
        if baseline is None or abs(it[2] - baseline) <= row_gap:
            current.append(it)
            baseline = it[2] if baseline is None else baseline
        else:
            rows.append(current)
            current = [it]
            baseline = it[2]
    if current:
        rows.append(current)

    lines = []
    for row in rows:
        row.sort(key=lambda it: it[1])
        cells = []
        current = row[0][0]
        prev_x1 = row[0][3]
        for ch, x0, y0, x1, y1 in row[1:]:
            if ch.isspace():
                continue
            if x0 - prev_x1 > space_gap:
                cells.append(current)
                current = ch
            else:
                current += ch
            prev_x1 = x1
        cells.append(current)
        lines.append(" ".join(cell for cell in cells if cell.strip()))
    return [line for line in lines if line]


def rows_from_pdfplumber(path, page_index):
    with pdfplumber.open(path) as pdf:
        text = pdf.pages[page_index].extract_text() or ""
    return [line.strip() for line in text.splitlines() if line.strip()]


mine = rows_from_pdfium(pdf_path, page_no - 1, row_gap, space_gap)
theirs = rows_from_pdfplumber(pdf_path, page_no - 1)
print(f"pdfium 行数 {len(mine)} / pdfplumber 行数 {len(theirs)}")
for i in range(max(len(mine), len(theirs))):
    a = mine[i] if i < len(mine) else "<缺>"
    b = theirs[i] if i < len(theirs) else "<缺>"
    flag = "  " if a == b else "!!"
    print(f"{flag} {a[:90]}")
    if a != b:
        print(f"   plumber: {b[:90]}")
