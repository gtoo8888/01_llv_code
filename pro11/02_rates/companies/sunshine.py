# -*- coding: utf-8 -*-
"""阳光人寿 阳光保E款 重大疾病保险 费率表。

这份表的坑：
- 32 页 = 方案（一/二）× 责任组合（4 种）× 体况（标准体 / B+50 / C+75 / D+100）。
  这三组维度的措辞是阳光自己的写法，所以解析规则放在本文件，不放 core。
- 版式是"左右两栏，各自带一条年龄列"：男左女右，每栏 5 个交费期。
  core 用"每条费率列取它左边最近的年龄列"来处理，不需要专门写分支。
- 单位是每千元，不是每万元。

样本断言取自第 1 页第一行：18 岁男性 5 年交 = 88.1。
"""

import re

from core import Spec

SAMPLE = {"age": 18, "gender": "男", "term": "5年交", "premium": 88.1}

PLAN_RE = re.compile(r"方案([一二三四五])")
RATE_CLASS_RE = re.compile(r"(标准体|次标准体)\s*费率\s*(?:([A-Z])\s*[（(]\s*\+?\s*(\d+)\s*[)）])?")
COVERAGE_RE = re.compile(r"(基本保险责任(?:\s*[+＋]\s*[^\s，。]+)*)")


def dims(text: str) -> dict:
    """从页首文字读出 方案 / 责任组合 / 体况。"""
    result = {"plan": "", "coverage": "", "rate_class": ""}

    match = PLAN_RE.search(text)
    if match:
        result["plan"] = "方案" + match.group(1)

    match = RATE_CLASS_RE.search(text)
    if match:
        label = match.group(1)
        if match.group(2):
            label = f"次标准体{match.group(2)}+{match.group(3)}"
        result["rate_class"] = label

    for line in text.split("\n"):
        match = COVERAGE_RE.search(line.strip())
        if match:
            result["coverage"] = match.group(1).replace(" ", "")
            break

    return result


def build_spec(pdf_path) -> Spec:
    return Spec(
        company="阳光人寿",
        product="阳光保E款重大疾病保险",
        unit_amount=1000,
        sample=SAMPLE,
        dims=dims,
        notes="32 页；双年龄列；标准体/次标准体 B/C/D",
    )
