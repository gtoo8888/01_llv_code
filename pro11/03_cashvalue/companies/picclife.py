# -*- coding: utf-8 -*-
"""人保寿险 无忧人生2026（成人版） 现金价值表。

这份表的形状：
- 3,550 页，每页约 60 行；首页有标题、单位说明和表头，其余页直接是数据。
- 6 列：保险责任、性别、交费期间、投保年龄、保单年度、现金价值。
  注意交费期间排在投保年龄**之前**，与阳光/新华的顺序不同。
- 交费期间写作 `一次性支付`，不是 `N年交`，引擎里按一次性处理（年限记 0）。
- 保险责任有组合值：`基本部分`、`基本部分+可选部分2`、`基本部分+可选部分2+可选部分3`。
- 单位是每万元基本保险金额。

取词上的坑（已由引擎处理）：
- `一`（一次性支付的第一个字）和 `+` 的字符框偏低/偏小，按 bbox 聚行会被拆成独立行；
  引擎改用字符原点作基线，这类字就归位了。

样本断言取自第 1 页：基本部分、男性、一次性支付、18 岁、保单年度 1 = 1561。
"""

from engine.spec import Spec

SAMPLE = {
    "gender": "男",
    "age": 18,
    "pay_term": "一次性支付",
    "coverage": "基本部分",
    "policy_year": 1,
    "cash_value": 1561,
}

FIELD_ORDER = ("coverage", "gender", "pay_term", "age", "policy_year", "cash_value")

# 人保写“男性/女性”
GENDER_ALIASES = {"男性": "男", "女性": "女"}


def build_spec(pdf_path) -> Spec:
    return Spec(
        company="人保寿险",
        product="无忧人生2026重大疾病保险（成人版）",
        unit_amount=10000,
        field_order=FIELD_ORDER,
        gender_aliases=GENDER_ALIASES,
        unit_note="每万元基本保险金额；货币单位为人民币元",
        samples=[SAMPLE],
        one_time_pay_terms=("一次性支付",),
        notes="3550 页；交费期间在年龄之前；责任有 +可选部分 组合",
    )
