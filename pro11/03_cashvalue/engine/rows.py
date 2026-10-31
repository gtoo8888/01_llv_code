# -*- coding: utf-8 -*-
"""把“单元格”变成“记录”：归一化、字段映射、宽表拆行、逐页解析。

这一层不碰 PDF，也不写文件；输入是 reader 产出的
`[{"no": 1, "rows": [[(x, "文本"), ...], ...]}]`，输出是结构化记录和页级日志。
"""

from __future__ import annotations

import re
from typing import List, Optional

from engine.spec import Spec

# 这三个是“这页根本不是表”的守卫，不该由 adapter 调
MIN_TEXT_CHARS = 50
MAX_AGE = 120
MAX_POLICY_YEAR = 200

NUM_RE = re.compile(r"^\d+(?:\.\d+)?$")
AGE_RE = re.compile(r"^(\d+)")
PAY_TERM_RE = re.compile(r"^(\d+)\s*年")
BARE_INT_RE = re.compile(r"^(\d+)$")     # 裸数字交费期，需 adapter 打开 pay_term_bare


def normalize_gender(text: str, aliases: dict) -> Optional[str]:
    return aliases.get(text.strip())


def normalize_age(text: str) -> Optional[int]:
    match = AGE_RE.match(text.strip())
    if not match:
        return None
    age = int(match.group(1))
    return age if 0 <= age <= MAX_AGE else None


def normalize_pay_term(text: str, one_time_terms: tuple, allow_bare: bool) -> Optional[tuple]:
    """把交费期归一成 ("5年交", 5)。

    - `5年` / `5年交` / `10 年交` 是结构写法，引擎直接认；
    - 裸数字 `5` 属于版式差异，只有 adapter 声明 `pay_term_bare=True` 时才接受；
    - `一次性支付` 之类的措辞由 adapter 的 `one_time_pay_terms` 提供。
    """
    text = text.strip()
    if text in one_time_terms:
        return "一次性支付", 0
    match = PAY_TERM_RE.match(text)
    if match is None and allow_bare:
        match = BARE_INT_RE.match(text)
    if not match:
        return None
    years = int(match.group(1))
    if years <= 0:
        return None
    return f"{years}年交", years


def map_cells(cells: list, spec: Spec):
    """单元格 → 字段字典。

    优先按顺序对齐（大多数表）；宽表允许缺格，此时按 x 归属到对应性别的列。
    """
    texts = [text for _x, text in cells]
    if len(cells) == len(spec.field_order):
        return dict(zip(spec.field_order, texts))

    if not (spec.value_columns and spec.value_x):
        return None

    prefix = [name for name in spec.field_order if name not in spec.value_columns]
    if len(cells) < len(prefix):
        return None
    values = dict(zip(prefix, texts[:len(prefix)]))
    for x, text in cells[len(prefix):]:
        for name, (left, right) in spec.value_x.items():
            if left <= x <= right:
                values[name] = text
                break
        else:
            return None
    return values


def parse_row(values: dict, spec: Spec) -> tuple:
    """字段字典 → 结构化行列表。长表 1 条，宽表（男女并列）按性别拆成多条。"""
    age = normalize_age(values["age"])
    if age is None:
        return [], f"年龄无法识别：{values['age']!r}"

    pay_term = normalize_pay_term(values["pay_term"], spec.one_time_pay_terms,
                                  spec.pay_term_bare)
    if pay_term is None:
        return [], f"交费期无法识别：{values['pay_term']!r}"
    pay_label, pay_years = pay_term

    try:
        policy_year = int(values["policy_year"])
    except ValueError:
        return [], f"保单年度不是数字：{values['policy_year']!r}"
    if not 1 <= policy_year <= MAX_POLICY_YEAR:
        return [], f"保单年度超出范围：{policy_year}"

    base = {
        "plan": values.get("plan", ""),
        "period": values.get("period", ""),
        "coverage": values.get("coverage", ""),
        "age": age,
        "pay_term": pay_label,
        "pay_term_years": pay_years,
        "policy_year": policy_year,
    }

    # 宽表：性别由列决定，一行拆成多条；某个性别没值就跳过
    if spec.value_columns:
        rows = []
        for field_name, gender in spec.value_columns.items():
            raw = values.get(field_name)
            if not raw:
                continue
            try:
                cash_value = float(raw)
            except ValueError:
                return [], f"现金价值不是数字：{field_name}={raw!r}"
            if cash_value < 0:
                return [], f"现金价值为负：{field_name}={cash_value}"
            rows.append({**base, "gender": gender, "cash_value": cash_value})
        if not rows:
            return [], "这一行没有现金价值"
        return rows, None

    if "gender" in spec.field_order:
        gender = normalize_gender(values["gender"], spec.gender_aliases)
        if gender is None:
            return [], f"性别无法识别：{values['gender']!r}"
    else:
        gender = ""

    try:
        cash_value = float(values["cash_value"])
    except ValueError:
        return [], f"现金价值不是数字：{values['cash_value']!r}"

    return [{**base, "gender": gender, "cash_value": cash_value}], None


def parse_pages(pages: list, spec: Spec) -> tuple:
    """页列表 → (rows, page_log, warnings)。逐页判定、逐行解析，单行失败不中断。"""
    rows: List[dict] = []
    page_log: List[dict] = []
    warnings: List[str] = []

    for page in pages:
        char_count = sum(len(text) for row in page["rows"] for _x, text in row)
        if char_count < MIN_TEXT_CHARS:
            page_log.append({"page": page["no"], "status": "skipped",
                             "reason": f"文字过少（{char_count} 字符）", "ignored": 0})
            continue

        page_rows, ignored, bad = [], 0, []
        for cells in page["rows"]:
            if not NUM_RE.match(cells[-1][1]):
                ignored += 1          # 表头 / 脚注：最后一格不是数字
                continue
            values = map_cells(cells, spec)
            if values is None:
                ignored += 1
                continue
            parsed, reason = parse_row(values, spec)
            if not parsed:
                bad.append(reason)
                continue
            for row in parsed:
                row["page"] = page["no"]
                page_rows.append(row)

        for reason in bad[:5]:
            warnings.append(f"第 {page['no']} 页：{reason}")

        if len(page_rows) < spec.thresholds.min_rows_per_page:
            page_log.append({"page": page["no"], "status": "skipped",
                             "reason": f"有效行 {len(page_rows)} < 阈值 {spec.thresholds.min_rows_per_page}",
                             "ignored": ignored})
            continue

        if ignored > spec.thresholds.max_ignored_lines:
            warnings.append(f"第 {page['no']} 页：忽略 {ignored} 行，超过阈值 {spec.thresholds.max_ignored_lines}")

        rows.extend(page_rows)
        page_log.append({"page": page["no"], "status": "parsed",
                         "rows": len(page_rows), "ignored": ignored})

    return rows, page_log, warnings
