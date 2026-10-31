# -*- coding: utf-8 -*-
"""03_cashvalue 的配置对象：Thresholds 与 Spec。

为什么单独一个文件
------------------
`companies/*.py` 只需要“声明这家怎么解析”，不应该连带加载 PDF 库。
Spec 放在这里，adapter 就只依赖配置，不依赖引擎的具体实现。

所有校验都在构造时完成：配置错了当场报错，不留到解析中途。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

FIELDS = (
    "plan",          # 方案（阳光：方案一/方案二）；没有就留空
    "period",        # 保险期间（阳光：终身）
    "coverage",      # 保险责任 / 责任组合
    "gender",
    "age",
    "pay_term",      # 归一成 “5年交”
    "policy_year",   # 保单年度末
    "cash_value",
)

GENDERS = {"男", "女"}


@dataclass
class Thresholds:
    """判定一页是不是有效数据页的门限。默认服务多数公司，特例在 adapter 覆盖。"""

    min_rows_per_page: int = 5      # 一页至少几行才算解析成功
    max_ignored_lines: int = 10     # 一页最多允许几行不像数据

    def __post_init__(self):
        if self.min_rows_per_page < 1:
            raise ValueError(f"min_rows_per_page 必须 ≥1，当前 {self.min_rows_per_page}")
        if self.max_ignored_lines < 0:
            raise ValueError(f"max_ignored_lines 不能为负，当前 {self.max_ignored_lines}")


@dataclass
class Spec:
    """一家公司、一份现金价值表的描述。由 companies/*.py 构造。"""

    company: str
    product: str
    unit_amount: int                        # 表内金额对应的保额（1000 / 10000）
    field_order: tuple                      # 每行 token 依次对应哪些字段
    gender_aliases: dict                    # 这家怎么写性别，如 {"男性": "男", "女性": "女"}
    unit_note: str = ""                     # 单位依据，写进 meta 与 validation
    pages: Optional[List[int]] = None       # 只解析这些页；None 表示全部
    samples: Optional[List[dict]] = None    # 抽样断言，可写多条；每条含 cash_value
    row_gap: float = 3.0                    # 同一行的基线容差（pt）；列不齐的公司在这里覆盖
    cell_gap: float = 6.0                   # 行内两个字段之间的最小间距（pt）；列密的公司调小
    one_time_pay_terms: tuple = ()          # 这家把“一次性交费”写成什么，如 ("一次性支付",)
    pay_term_bare: bool = False             # 交费期是否写成裸数字（太保：`5` 而不是 `5年`）
    value_columns: dict = field(default_factory=dict)   # 宽表：{字段名: 性别}，如 {"cash_value_male": "男"}
    value_x: dict = field(default_factory=dict)         # 宽表缺格时按 x 归属：{字段名: (左, 右)}
    thresholds: Thresholds = field(default_factory=Thresholds)
    notes: str = ""

    def __post_init__(self):
        if not self.company or not self.product:
            raise ValueError("company 和 product 不能为空")
        if self.unit_amount <= 0:
            raise ValueError(f"unit_amount 必须 > 0，当前 {self.unit_amount}")
        if self.row_gap <= 0:
            raise ValueError(f"row_gap 必须 > 0，当前 {self.row_gap}")
        if self.cell_gap <= 0:
            raise ValueError(f"cell_gap 必须 > 0，当前 {self.cell_gap}")
        if any(not isinstance(term, str) or not term for term in self.one_time_pay_terms):
            raise ValueError(f"one_time_pay_terms 必须是非空字符串：{self.one_time_pay_terms!r}")
        if not self.value_columns and not self.gender_aliases:
            raise ValueError("长表必须在 gender_aliases 里声明这家怎么写性别")
        bad = {
            key: value for key, value in self.gender_aliases.items()
            if not key or value not in GENDERS
        }
        if bad:
            raise ValueError(f"gender_aliases 的值只能是 {sorted(GENDERS)}：{bad}")
        if not self.field_order:
            raise ValueError("field_order 不能为空")
        unknown = set(self.field_order) - set(FIELDS) - set(self.value_columns)
        if unknown:
            raise ValueError(f"field_order 里有未知字段：{sorted(unknown)}")
        if len(set(self.field_order)) != len(self.field_order):
            raise ValueError(f"field_order 有重复字段：{self.field_order}")
        required = {"age", "pay_term", "policy_year"}
        if not self.value_columns:
            required.add("cash_value")
        missing = required - set(self.field_order)
        if missing:
            raise ValueError(f"field_order 缺少必需字段：{sorted(missing)}")

        if self.value_columns:
            # 宽表：一行里有多个性别的现金价值，性别由列决定，不能同时再有性别列
            if "gender" in self.field_order:
                raise ValueError("宽表（value_columns）不能再有 gender 列")
            not_in_order = set(self.value_columns) - set(self.field_order)
            if not_in_order:
                raise ValueError(f"value_columns 不在 field_order 里：{sorted(not_in_order)}")
            bad = {key: g for key, g in self.value_columns.items() if g not in GENDERS}
            if bad:
                raise ValueError(f"value_columns 的性别只能是 {sorted(GENDERS)}：{bad}")
            unknown = set(self.value_x) - set(self.value_columns)
            if unknown:
                raise ValueError(f"value_x 里有未知字段：{sorted(unknown)}")
            for name, bounds in self.value_x.items():
                if len(bounds) != 2 or bounds[0] >= bounds[1]:
                    raise ValueError(f"value_x 的区间不合法：{name}={bounds!r}")
        elif "cash_value" not in self.field_order:
            raise ValueError("长表必须在 field_order 里包含 cash_value")

        if self.pages is not None:
            if not self.pages:
                raise ValueError("pages 为空列表；表示“全部页”请用 None")
            if any(page < 1 for page in self.pages):
                raise ValueError(f"pages 必须从 1 开始，当前 {self.pages}")

        if self.samples is not None:
            if not self.samples:
                raise ValueError("samples 为空列表；不做抽样断言请用 None")
            for sample in self.samples:
                if not isinstance(sample, dict):
                    raise ValueError(f"samples 的每条必须是 dict：{sample!r}")
                unknown = set(sample) - set(FIELDS) - {"cash_value"} - set(self.value_columns)
                if unknown:
                    raise ValueError(f"samples 里有未知字段：{sorted(unknown)}")
                if "cash_value" not in sample:
                    raise ValueError(f"samples 的每条都要有 cash_value：{sample!r}")
