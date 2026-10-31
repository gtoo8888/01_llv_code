# -*- coding: utf-8 -*-
"""中国人寿 康宁乐享终身重大疾病保险 费率表。

这份表的坑：
- **单页**，页面尺寸 1044×1477，比别家 A4 大一倍左右。
  列间距、字号、数字宽度都跟着放大，考验 core 的绝对点数容差（column_tolerance）。
- 男女并排，各 7 个交费期：一次性交付 / 3 / 5 / 6 / 8 / 10 / 20 年交。
- 表头同样是 "3" + "年交" 拆开写，且基线不完全对齐，靠 core 的双向合并处理。
- 没有 方案 / 责任 / 体况 维度。

样本断言取自第一行：0 岁男性 一次性交付 = 3913。
"""

from core import Spec

SAMPLE = {"age": 0, "gender": "男", "term": "一次性交付", "premium": 3913}


def build_spec(pdf_path) -> Spec:
    return Spec(
        company="中国人寿",
        product="康宁乐享终身重大疾病保险",
        unit_amount=10000,
        sample=SAMPLE,
        notes="单页 1044×1477；男女各 7 个交费期",
    )
