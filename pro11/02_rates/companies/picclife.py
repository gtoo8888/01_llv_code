# -*- coding: utf-8 -*-
"""人保寿险 无忧人生2026（成人版）重大疾病保险 费率表。

这份表的坑：
- **一页里会叠两张表**：p4 上半是上一节的结尾（58–62 岁），下半是新一节
  （保险责任 基本部分+可选部分1+可选部分2）的表头 + 18 岁起的数据。
  本文件按 "保险责任 ..." 表头把同一页切成两个块，core 分别解析。
- 年龄段被拆到多页，单页可能只有 5–8 个年龄，所以把“年龄跨度”门限调低。
- 维度写在 "保险责任 基本部分" 这样的行里，用 dims 提取。

样本断言取自第 1 页：18 岁男性 一次性支付 = 4452。
"""

import re

from core import Spec, Thresholds

SAMPLE = {"age": 18, "gender": "男", "term": "一次性支付", "premium": 4452}

COVERAGE_RE = re.compile(r"保险责任\s*(\S+)")
# 一页里新一节费率表的起点；行内拼接后没有空格，所以不能用 \s
BLOCK_MARKER = re.compile(r"^保险责任(?!\d)")


def dims(text: str) -> dict:
    """从 "保险责任 基本部分[+可选部分N]" 行读出责任组合。"""
    result = {"plan": "", "coverage": "", "rate_class": ""}
    for line in text.split("\n"):
        match = COVERAGE_RE.search(line.strip())
        if match:
            result["coverage"] = match.group(1)
            break
    return result


def split_blocks(page: dict) -> list:
    """把一页按 "保险责任 ..." 行切成上下两块。

    别的公司一页只有一张表；人保会把上一节的结尾和新一节的表头叠在同一页，
    不切开就会把两节的数据混在一起。切法是按行的 y 坐标区间切，
    只在本公司的版式上验证过，所以放在这里而不是 core。
    """
    words = page["words"]
    if not words:
        return [{"words": [], "text": page["text"]}]

    ordered = sorted(words, key=lambda w: w["top"])
    lines = []
    current = []
    anchor = None
    for word in ordered:
        if anchor is None or abs(word["top"] - anchor) <= 3:
            current.append(word)
            if anchor is None:
                anchor = word["top"]
        else:
            lines.append((anchor, current))
            current = [word]
            anchor = word["top"]
    if current:
        lines.append((anchor, current))

    line_texts = [
        (top, "".join(word["text"] for word in sorted(line, key=lambda w: w["x0"])))
        for top, line in lines
    ]

    markers = [top for top, text in line_texts if BLOCK_MARKER.match(text.strip())]
    if not markers:
        return [{"words": words, "text": page["text"]}]

    low = min(word["top"] for word in words) - 1
    high = max(word["top"] for word in words) + 1
    bounds = [low] + markers + [high]

    blocks = []
    for start, end in zip(bounds, bounds[1:]):
        block_words = [word for word in words if start <= word["top"] < end]
        if not block_words:
            continue
        text = "\n".join(item for top, item in line_texts if start <= top < end)
        blocks.append({"words": block_words, "text": text})
    return blocks


def build_spec(pdf_path) -> Spec:
    return Spec(
        company="人保寿险",
        product="无忧人生2026（成人版）重大疾病保险",
        unit_amount=10000,
        sample=SAMPLE,
        dims=dims,
        split_blocks=split_blocks,
        # 一份表被拆到多页，单页年龄少、行也少
        thresholds=Thresholds(min_age_values=5, min_age_span=3, min_rows=5),
        notes="一页可能叠两节；按 保险责任 表头切块",
    )
