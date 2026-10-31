# -*- coding: utf-8 -*-
"""新华保险 健康无忧卓越版 现金价值表。

这份表的形状：
- 1,180 页，每页约 70 行；每页顶部有两行跑马表头（标题 + 公司名），不是数据。
- 列顺序固定为 6 个字段，比阳光少“方案”“保险期间”。
- 年龄 0 岁写成 `0（须出生满30日）`，取开头的数字即可，不会被丢掉。
- 交费方式写作 `5年交`，与阳光的 `5年` 不同，引擎统一归一成 “N年交”。
- 表头写的是“基本保险金额：10000元 单位：元”，即表内金额对应 1 万元保额。

样本断言取自第 1 页：基本责任、男、0 岁、5 年交、保单年度 1 = 94。
"""

from engine.spec import Spec

SAMPLE = {
    "gender": "男",
    "age": 0,
    "pay_term": "5年交",
    "coverage": "基本责任",
    "policy_year": 1,
    "cash_value": 94,
}

FIELD_ORDER = ("coverage", "gender", "age", "pay_term", "policy_year", "cash_value")

# 新华写“男/女”
GENDER_ALIASES = {"男": "男", "女": "女"}


def build_spec(pdf_path) -> Spec:
    return Spec(
        company="新华保险",
        product="健康无忧卓越版重大疾病保险",
        unit_amount=10000,
        field_order=FIELD_ORDER,
        gender_aliases=GENDER_ALIASES,
        unit_note="基本保险金额 10000 元，表内单位为元",
        samples=[SAMPLE],
        notes="1180 页；每页顶部两行跑马表头；年龄含 0 岁写法",
    )
