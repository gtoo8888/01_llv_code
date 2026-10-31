"""阶段 1：侦察——抓取每只基金的基本概况页与费率页，落快照。

数据源：天天基金 f10 页面（线索层，非最终证据）。
最终证据仍以基金公司官网 / 证监会披露的 PDF 为准。

用法：
    python 01_discover.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    DATA,
    HTML,
    add_manifest,
    decode,
    ensure_dirs,
    get,
    log,
    safe_name,
    save_bytes,
    sha256,
    today,
)

PAGES = {
    "jbgk": "https://fundf10.eastmoney.com/jbgk_{code}.html",  # 基本概况
    "jjfl": "https://fundf10.eastmoney.com/jjfl_{code}.html",  # 基金费率
    "jdzf": "https://fundf10.eastmoney.com/jdzf_{code}.html",  # 阶段涨幅
}


def load_universe() -> dict:
    path = Path(__file__).resolve().parent / "config" / "universe.json"
    return json.loads(path.read_text(encoding="utf-8"))


def targets(uni: dict) -> list[dict]:
    out = []
    for f in uni["funds"]:
        etf = f["etf"]
        out.append(
            {"code": etf["code"], "role": "ETF", "company": f["company"], "name": etf["name"]}
        )
        for fd in f["feeder"]:
            out.append(
                {
                    "code": fd["code"],
                    "role": f"联接{fd['class']}",
                    "company": f["company"],
                    "name": fd["name"],
                }
            )
    return out


def main() -> None:
    ensure_dirs()
    uni = load_universe()
    records = []
    for t in targets(uni):
        for key, tpl in PAGES.items():
            url = tpl.format(code=t["code"])
            fname = f"{today()}_{t['code']}_{key}.html"
            path = HTML / fname
            if path.exists():
                log(f"SKIP exists {fname}")
                continue
            r = get(url)
            if r is None:
                log(f"MISS {t['code']} {key}")
                continue
            html = decode(r)
            save_bytes(path, r.content)
            records.append(
                {
                    "code": t["code"],
                    "role": t["role"],
                    "name": t["name"],
                    "page": key,
                    "url": url,
                    "path": str(path.relative_to(DATA.parent)),
                    "fetched_at": datetime.now().isoformat(timespec="seconds"),
                    "http": r.status_code,
                    "bytes": len(r.content),
                    "sha256": sha256(path),
                }
            )
            log(f"OK {t['code']} {key} {len(r.content)}B")
    add_manifest(records)
    log(f"done: {len(records)} snapshots")


if __name__ == "__main__":
    main()
