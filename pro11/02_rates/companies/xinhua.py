# -*- coding: utf-8 -*-
"""新华保险 健康无忧卓越版重大疾病保险 费率表。

这份表的坑：
- 89 页里**只有前 2 页是费率网格**：
  第 1 页 基本责任，第 2 页 基本责任+可选责任；
  第 3 页起是"次标准体评点加费"，字段完全不同，用 pages 白名单排除。
- 年龄 0 岁那行写成 `0（须出生满30日）`，不是纯数字，会被丢掉。
  当前解析范围是 1–65 岁，0 岁缺失是已知取舍。
- 维度写在 "基本责任 基本保险金额：10000元" 这种行首，用 dims 提取。
- 男女各 5 个交费期（5/10/15/20/30 年交），单位每万元。

样本断言取自第 1 页：1 岁男性 5 年交 = 780。
"""

import re

from core import Spec

SAMPLE = {"age": 1, "gender": "男", "term": "5年交", "premium": 780}

COVERAGE_RE = re.compile(r"^(基本责任(?:\+可选责任)?)")


def dims(text: str) -> dict:
    """从 "基本责任[+可选责任] ..." 行读出责任组合。"""
    result = {"plan": "", "coverage": "", "rate_class": ""}
    for line in text.split("\n"):
        match = COVERAGE_RE.match(line.strip())
        if match:
            result["coverage"] = match.group(1)
            break
    return result


def build_spec(pdf_path) -> Spec:
    return Spec(
        company="新华保险",
        product="健康无忧卓越版重大疾病保险",
        unit_amount=10000,
        pages=[1, 2],
        sample=SAMPLE,
        dims=dims,
        notes="仅前 2 页为网格；0 岁行因年龄格含文字被跳过",
    )
