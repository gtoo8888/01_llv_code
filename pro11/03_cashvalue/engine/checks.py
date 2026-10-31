# -*- coding: utf-8 -*-
"""校验：重复行、负值、保单年度连续性、抽样断言。

只读 rows 和 spec，不改数据、不碰文件。
"""

from __future__ import annotations

from typing import List

from engine.spec import Spec


def validate(rows: List[dict], spec: Spec, warnings: List[str]) -> List[str]:
    errors: List[str] = []

    seen = {}
    for row in rows:
        key = (row["plan"], row["period"], row["coverage"], row["gender"],
               row["age"], row["pay_term_years"], row["policy_year"])
        if key in seen:
            errors.append(f"重复行：{key}（第 {seen[key]} 页与第 {row['page']} 页）")
        else:
            seen[key] = row["page"]
        if row["cash_value"] < 0:
            errors.append(f"现金价值为负：{key} = {row['cash_value']}")

    if spec.pages is None:
        groups = {}
        for row in rows:
            groups.setdefault((row["plan"], row["period"], row["coverage"], row["gender"],
                               row["age"], row["pay_term_years"]), set()).add(row["policy_year"])
        for key, years in sorted(groups.items()):
            highest = max(years)
            expected = set(range(1, highest + 1))
            if years != expected:
                gaps = sorted(expected - years)
                warnings.append(f"保单年度不连续：{key} 缺 {gaps[:10]}{'…' if len(gaps) > 10 else ''}")
    else:
        warnings.append("只解析了部分页，已跳过保单年度连续性与抽样断言")

    if spec.pages is None and spec.samples is not None:
        for sample in spec.samples:
            target = {key: value for key, value in sample.items() if key != "cash_value"}
            matched = [
                row for row in rows
                if all(row.get(key) == value for key, value in target.items())
            ]
            label = "，".join(f"{key}={value}" for key, value in target.items())
            if not matched:
                errors.append(f"抽样断言失败：找不到 {label}")
                continue
            actual = matched[0]["cash_value"]
            if abs(actual - sample["cash_value"]) > 1e-6:
                errors.append(
                    f"抽样断言失败：{label} 期望 {sample['cash_value']}，实际 {actual}"
                )

    return errors
