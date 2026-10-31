# -*- coding: utf-8 -*-
"""输出层：每份 PDF 一套产物（long CSV / meta.json / validation.md）。

只写文件，不做校验、不做解析。文本 IO 统一走 01_pdf/parse_utils。
"""

from __future__ import annotations

import csv
import io
import sys
from datetime import datetime
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "01_pdf"))
from parse_utils import write_json, write_text  # noqa: E402

from engine.spec import Spec  # noqa: E402

PARSER_NAME = "03_cashvalue"


def write_outputs(doc_dir: Path, stem: str, pdf_path: Path, digest: str, rows: List[dict],
                  unit: int, unit_note: str, page_log: List[dict], errors: List[str],
                  warnings: List[str], total_pages: int, spec: Spec) -> None:
    doc_dir.mkdir(parents=True, exist_ok=True)

    headers = ["company", "product", "plan", "period", "coverage", "gender", "age",
               "pay_term", "pay_term_years", "policy_year", "cash_value",
               "unit_amount", "cash_value_per_1000", "page"]
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    for row in sorted(rows, key=lambda r: (r["plan"], r["period"], r["coverage"], r["gender"],
                                           r["age"], r["pay_term_years"], r["policy_year"])):
        writer.writerow([
            spec.company, spec.product, row["plan"], row["period"], row["coverage"],
            row["gender"], row["age"], row["pay_term"], row["pay_term_years"],
            row["policy_year"], row["cash_value"], unit,
            round(row["cash_value"] * 1000 / unit, 4), row["page"],
        ])
    write_text(doc_dir / "cashvalue_long.csv", buffer.getvalue())

    meta = {
        "source": {"file": pdf_path.name, "sha256": digest,
                   "bytes": pdf_path.stat().st_size, "pages": total_pages},
        "company": {"name": spec.company, "product": spec.product},
        "unit": {"amount": unit, "note": unit_note},
        "parser": {"name": PARSER_NAME,
                   "parsed_at": datetime.now().astimezone().isoformat(timespec="seconds")},
        "spec": {"field_order": list(spec.field_order), "pages": spec.pages,
                 "samples": spec.samples, "value_columns": spec.value_columns,
                 "notes": spec.notes},
        "stats": {
            "records": len(rows),
            "parsed_pages": sum(1 for item in page_log if item["status"] == "parsed"),
            "skipped_pages": sum(1 for item in page_log if item["status"] == "skipped"),
        },
        "pages": page_log,
    }
    write_json(doc_dir / "meta.json", meta)

    lines = [f"# 校验 · {stem}", ""]
    lines.append(f"- 源文件：`{pdf_path.name}`")
    lines.append(f"- 公司/产品：{spec.company} / {spec.product}")
    lines.append(f"- 单位：每 {unit} 元基本保险金额（{unit_note or '未注明'}）")
    lines.append(f"- 解析页：{meta['stats']['parsed_pages']}，跳过页：{meta['stats']['skipped_pages']}")
    lines.append(f"- 记录数：{len(rows)}")
    if spec.notes:
        lines.append(f"- 备注：{spec.notes}")
    lines.append("")
    lines.append("## 逐页")
    lines.append("")
    lines.append("| 页 | 状态 | 说明 | 忽略行 |")
    lines.append("|---:|---|---|---:|")
    for item in page_log:
        detail = item.get("reason") or f"{item.get('rows', 0)} 行"
        lines.append(f"| {item['page']} | {item['status']} | {detail} | {item.get('ignored', 0)} |")
    lines.append("")
    lines.append("## 错误")
    lines.append("")
    lines.extend([f"- {item}" for item in errors] or ["- 无"])
    lines.append("")
    lines.append("## 警告")
    lines.append("")
    lines.extend([f"- {item}" for item in warnings[:50]] or ["- 无"])
    if len(warnings) > 50:
        lines.append(f"- …… 另有 {len(warnings) - 50} 条警告")
    lines.append("")
    write_text(doc_dir / "validation.md", "\n".join(lines) + "\n")
