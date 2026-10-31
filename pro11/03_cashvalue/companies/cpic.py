# -*- coding: utf-8 -*-
"""太平洋人寿 金生无忧2025（成人版） 现金价值表。

这份表的形状：
- 287 页，每页约 50 行；表头分两行印（列名一行、`男性 女性` 一行），只在第 1 页。
- **男女并列两列**：一行同时给两个现金价值，和阳光/新华/人保的“一行一个性别”不同。
  引擎用 `value_columns` 把一行拆成两条记录。
- 列顺序：交费期间、保险期间、投保年龄、保单年度、男、女。
- 交费期间写成裸数字 `1` / `5` / `15`，没有“年”字，引擎按 `N年交` 归一。
- 单位是每 10,000 元基本保险金额。

来源（抓取日期 2026-10-23）：
  http://life.cpic.com.cn/upload/resources/file/2025/08/13/88559.pdf
  入口：官网 → 公开信息披露 → 在售产品 → 健康险 第 7 页

样本断言取自第 1 页：交费期间 1、终身、18 岁、保单年度 1，男 1926 / 女 1720。
"""

from engine.spec import Spec

SAMPLES = [
    {"gender": "男", "period": "终身", "age": 18, "pay_term": "1年交",
     "policy_year": 1, "cash_value": 1926},
    {"gender": "女", "period": "终身", "age": 18, "pay_term": "1年交",
     "policy_year": 1, "cash_value": 1720},
]

FIELD_ORDER = ("pay_term", "period", "age", "policy_year",
               "cash_value_male", "cash_value_female")

VALUE_COLUMNS = {"cash_value_male": "男", "cash_value_female": "女"}

# 有些组合（如 30 年交、部分高龄）只印一个性别的值，另一格是空白。
# 按单元格的 x 判断它属于哪一列：男 ≈355，女 ≈471（单位 pt）。
VALUE_X = {"cash_value_male": (320, 415), "cash_value_female": (430, 530)}


def build_spec(pdf_path) -> Spec:
    return Spec(
        company="太平洋人寿",
        product="金生无忧2025（成人版）重大疾病保险",
        unit_amount=10000,
        field_order=FIELD_ORDER,
        gender_aliases={},                  # 宽表没有性别列，性别由列决定
        value_columns=VALUE_COLUMNS,
        value_x=VALUE_X,
        pay_term_bare=True,                 # 这家交费期写成裸数字 `1` / `5` / `15`
        samples=SAMPLES,
        unit_note="每 10,000 元基本保险金额",
        notes="287 页；男女并列两列；部分组合只有单性别；交费期间写作裸数字",
    )
