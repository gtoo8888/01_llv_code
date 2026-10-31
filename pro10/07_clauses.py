"""阶段 6：条款核查——从招募说明书里抽两条关键条款。

1) 不重复收费：联接基金投资于目标 ETF 的部分是否免收管理费/托管费
2) 黄金租赁：基金是否允许把持有的黄金现货合约借出/租赁

输出 data/clauses.json，供报告引用。

用法：
    python 07_clauses.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pdfplumber  # noqa: E402

from lib.common import DATA, log  # noqa: E402

NO_DOUBLE = [
    r"不收取管理费",
    r"避免重复收费",
    r"不计提基金管理费",
    r"不计提管理费",
    r"不对.{0,20}计提管理费",
    r"不重复收取",
    r"扣除.{0,50}目标\s*ETF.{0,50}后.{0,15}(剩余部分|净额)",
]
LEASING = [r"借出", r"租赁", r"租借"]


def scan() -> None:
    manifest = [
        r
        for r in json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
        if r.get("category") == "prospectus"
    ]

    # 同一份招募说明书可能被多个份额共用，按 sha 去重
    seen: dict[str, dict] = {}
    for rec in manifest:
        seen.setdefault(rec["sha256"], rec)

    out: dict[str, dict] = {}
    for sha, rec in seen.items():
        path = DATA.parent / rec["path"]
        try:
            with pdfplumber.open(path) as pdf:
                pages = [(i + 1, p.extract_text() or "") for i, p in enumerate(pdf.pages)]
        except Exception as e:  # noqa: BLE001
            log(f"PDF FAIL {path.name}: {e}")
            continue
        full = "\n".join(t for _, t in pages)

        hit_no_double = None
        for pat in NO_DOUBLE:
            m = re.search(pat, full)
            if m:
                page = next((n for n, t in pages if re.search(pat, t)), None)
                hit_no_double = {"match": m.group(0), "page": page}
                break

        lease_hits = []
        for pat in LEASING:
            for m in re.finditer(pat, full):
                page = next((n for n, t in pages if pat in t), None)
                snippet = full[max(0, m.start() - 50) : m.start() + 80].replace("\n", " ")
                lease_hits.append({"match": m.group(0), "page": page, "snippet": snippet})
                break

        out[rec["code"]] = {
            "file": Path(rec["path"]).name,
            "title": rec["title"],
            "sha8": sha[:8],
            "pages": len(pages),
            "no_double_charge": hit_no_double,
            "leasing": lease_hits,
        }
        log(
            f"{rec['code']} pages={len(pages)} "
            f"不重复收费={'✅ p'+str(hit_no_double['page']) if hit_no_double else '❌'} "
            f"租赁={len(lease_hits)}处"
        )

    (DATA / "clauses.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log(f"clauses -> data/clauses.json ({len(out)} 份招募说明书)")


if __name__ == "__main__":
    scan()
