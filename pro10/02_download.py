"""阶段 3：下载——按公告标题筛出关键 PDF 并落盘。

来源：天天基金公告接口（镜像），PDF 托管于 pdf.dfcfw.com。
每份记录来源公告 ID、发布日期、原始 URL、sha256，供 report 引用页码。

用法：
    python 02_download.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    DATA,
    RAW,
    add_manifest,
    ensure_dirs,
    get,
    log,
    sha256,
    today,
)

API = "https://api.fund.eastmoney.com/f10/JJGG"
PDF = "http://pdf.dfcfw.com/pdf/H2_{id}_1.pdf"
REFERER = {"Referer": "https://fundf10.eastmoney.com/"}

# 关键词 -> 产物类别；顺序即优先级
RULES = [
    ("招募说明书", "prospectus"),
    ("产品资料概要", "summary"),
    ("基金合同", "contract"),
    ("季度报告", "quarterly"),
    ("中期报告", "interim"),
    ("年度报告", "annual"),
    ("费率", "fee_notice"),
    ("暂停申购", "suspend"),
    ("限制", "suspend"),
    ("大额申购", "suspend"),
]

MAX_PAGES = 12


def list_announcements(code: str) -> list[dict]:
    out: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        r = get(
            API,
            params={"fundcode": code, "pageIndex": page, "pageSize": 50, "type": "0"},
            extra_headers=REFERER,
        )
        if r is None:
            break
        try:
            d = r.json()
        except Exception:  # noqa: BLE001
            log(f"json fail {code} p{page}")
            break
        items = d.get("Data") or []
        if not items:
            break
        out.extend(items)
        total = d.get("TotalCount") or 0
        if len(out) >= total:
            break
        time.sleep(0.5)
    return out


def classify(title: str) -> str | None:
    for kw, cat in RULES:
        if kw in title:
            return cat
    return None


def pick_latest(items: list[dict], code: str) -> dict[str, dict]:
    """每个类别取最新一份。"""
    best: dict[str, dict] = {}
    for it in items:
        cat = classify(it.get("TITLE", ""))
        if not cat:
            continue
        if cat not in best:
            best[cat] = it
    return best


def main() -> None:
    ensure_dirs()
    uni = json.loads(
        (Path(__file__).resolve().parent / "config" / "universe.json").read_text(encoding="utf-8")
    )
    codes = []
    for f in uni["funds"]:
        codes.append(f["etf"]["code"])
        codes.extend(x["code"] for x in f["feeder"])

    records = []
    for code in codes:
        items = list_announcements(code)
        log(f"{code}: {len(items)} announcements")
        picks = pick_latest(items, code)
        for cat, it in picks.items():
            aid = it.get("ID")
            if not aid:
                continue
            url = PDF.format(id=aid)
            fname = f"{today()}_{code}_{cat}.pdf"
            path = RAW / fname
            if path.exists():
                log(f"SKIP exists {fname}")
                continue
            r = get(url, timeout=60)
            if r is None or not r.content.startswith(b"%PDF"):
                log(f"BAD PDF {code} {cat} {url}")
                continue
            path.write_bytes(r.content)
            records.append(
                {
                    "code": code,
                    "category": cat,
                    "title": it.get("TITLE"),
                    "announcement_id": aid,
                    "published": (it.get("PUBLICATIONDATE") or "")[:10],
                    "url": url,
                    "path": str(path.relative_to(DATA.parent)),
                    "fetched_at": datetime.now().isoformat(timespec="seconds"),
                    "bytes": len(r.content),
                    "sha256": sha256(path),
                    "source": "天天基金公告镜像（原文由基金公司报送）",
                }
            )
            log(f"OK {code} {cat} {len(r.content)//1024}KB {it.get('TITLE')[:40]}")
            time.sleep(1.2)
    add_manifest(records)
    log(f"done: {len(records)} pdfs")


if __name__ == "__main__":
    main()
