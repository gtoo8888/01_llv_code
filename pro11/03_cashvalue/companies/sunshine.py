# -*- coding: utf-8 -*-
"""阳光人寿 阳光保E款 现金价值表。

这份表的形状：
- 2,396 页，每页约 76 行；表头只出现在第 1 页，其余页直接是数据。
- 每一行都重复写全部维度（交费期间 / 保险期间 / 方案 / 保险责任 / 性别 /
  年龄 / 保单年度），所以不存在“跨页继承表头”的问题。
- 列顺序固定为 8 个字段，字段之间用空格分隔；保险责任里带括号也不会拆词。
- 单位是每千元基本保险金额，与费率表一致。

样本断言取自第 1 页：男性、18 岁、5 年交、方案一、基本保险责任、保单年度 1 = 14.5。
"""

from engine.spec import Spec

SAMPLE = {
    "gender": "男",
    "age": 18,
    "pay_term": "5年交",
    "plan": "方案一",
    "period": "终身",
    "coverage": "基本保险责任",
    "policy_year": 1,
    "cash_value": 14.5,
}

FIELD_ORDER = ("pay_term", "period", "plan", "coverage",
               "gender", "age", "policy_year", "cash_value")

# 阳光写“男性/女性”
GENDER_ALIASES = {"男性": "男", "女性": "女"}


def build_spec(pdf_path) -> Spec:
    return Spec(
        company="阳光人寿",
        product="阳光保E款重大疾病保险",
        unit_amount=1000,
        field_order=FIELD_ORDER,
        gender_aliases=GENDER_ALIASES,
        unit_note="每千元基本保险金额对应的现金价值（单位：元）",
        samples=[SAMPLE],
        notes="2396 页；表头仅第 1 页；交费期间写作 `5年`",
    )
