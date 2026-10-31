# -*- coding: utf-8 -*-
"""平安人寿 安佑福（全能版）重大疾病保险 费率表。

这份表的坑：
- 2 页，**每页只有一个性别**：第 1 页男性，第 2 页女性。
  每页表头只出现一个性别词，core 按"最近性别词"映射，整页归同一性别。
- 每页 4 个交费期（10/15/20/30 年交），年龄 0–55。
- 单位是每万元。

样本断言取自第 1 页第一行：0 岁男性 10 年交 = 408。
"""

from core import Spec

SAMPLE = {"age": 0, "gender": "男", "term": "10年交", "premium": 408}


def build_spec(pdf_path) -> Spec:
    return Spec(
        company="平安人寿",
        product="安佑福（全能版）重大疾病保险",
        unit_amount=10000,
        sample=SAMPLE,
        notes="每页单一性别（第 1 页男、第 2 页女），年龄 0–55",
    )
