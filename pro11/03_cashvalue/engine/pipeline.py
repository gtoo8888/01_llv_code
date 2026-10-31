#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单文档流程：一份 PDF + 一个 Spec → 一套产物（或只出结果）。

四步被抽成四个模块，这里只负责**按顺序调用**并把结果装进 Result：

    reader.read_pages   读页     （唯一依赖 PDF 库的地方）
    rows.parse_pages    解析     （单元格 → 记录）
    checks.validate     校验     （重复、连续性、抽样断言）
    writer.write_outputs 输出    （CSV / meta / validation）

两个接缝
--------
- `reader`：默认 `engine.reader.read_pages`。换成假数据就能跳过 PDF 测下游。
- `writer`：默认 `engine.writer.write_outputs`。传 `None` 就是 dry-run——只解析不落盘。

不做结果缓存：每次都重新解析，产物只由本次输入决定。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from engine.checks import validate
from engine.reader import read_pages, sha256_of
from engine.rows import parse_pages
from engine.spec import Spec
from engine.writer import write_outputs


@dataclass
class Result:
    """一次解析的结果。成功与否看 `status`，失败原因看 `reason`。"""

    file: str
    status: str = "ok"              # ok / warning / failed
    rows: int = 0
    parsed_pages: int = 0
    skipped_pages: int = 0
    total_pages: int = 0
    unit: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    reason: str = ""                # 仅 failed 时有值


class Pipeline:
    """一份 PDF 走完四步。构造时传入 Spec，调用 run() 执行。"""

    def __init__(self, spec: Spec, *, reader=read_pages, writer=write_outputs):
        self.spec = spec
        self.reader = reader
        self.writer = writer

    def run(self, pdf_path: Path, out_dir: Optional[Path] = None) -> Result:
        spec = self.spec
        digest = sha256_of(pdf_path)

        pages, total_pages = self.reader(pdf_path, spec)
        if not pages:
            return Result(file=pdf_path.name, status="failed", total_pages=total_pages,
                          reason="没有可解析的页（pages 超出总页数？）")

        rows, page_log, warnings = parse_pages(pages, spec)
        if not rows:
            return Result(file=pdf_path.name, status="failed", total_pages=total_pages,
                          reason="没有解析出任何数据行")

        for row in rows:
            row["cash_value_per_1000"] = round(row["cash_value"] * 1000 / spec.unit_amount, 4)

        errors = validate(rows, spec, warnings)

        if self.writer is not None and out_dir is not None:
            self.writer(out_dir / pdf_path.stem, pdf_path.stem, pdf_path, digest, rows,
                        spec.unit_amount, spec.unit_note, page_log, errors, warnings,
                        total_pages, spec)

        return Result(
            file=pdf_path.name,
            status="ok" if not errors else "warning",
            rows=len(rows),
            parsed_pages=sum(1 for item in page_log if item["status"] == "parsed"),
            skipped_pages=sum(1 for item in page_log if item["status"] == "skipped"),
            total_pages=total_pages,
            unit=spec.unit_amount,
            errors=errors,
            warnings=warnings,
        )


def parse(pdf_path: Path, spec: Spec, out_dir: Path) -> Result:
    """便捷入口，等价于 Pipeline(spec).run(pdf_path, out_dir)。"""
    return Pipeline(spec).run(pdf_path, out_dir)
