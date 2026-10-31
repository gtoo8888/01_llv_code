"""阶段 5：全市场扫描——把"黄金"相关基金全部拉一遍，做初筛。

产出 data/survey.json + data/survey.md，用于决定下一轮深挖哪几只。
不下载 PDF，只抓基本概况页（轻量）。

用法：
    python 06_survey.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import DATA, decode_bytes, get, log, strip_tags  # noqa: E402

LIST_URL = "http://fund.eastmoney.com/js/fundcode_search.js"
JBGK = "https://fundf10.eastmoney.com/jbgk_{code}.html"


def load_fund_list() -> list[list[str]]:
    r = get(LIST_URL, timeout=40)
    if r is None:
        raise SystemExit("fund list unavailable")
    text = decode_bytes(r.content)
    raw = text[text.find("[[") : text.rfind("]]") + 2]
    return json.loads(raw)


def parse(text: str) -> dict:
    def pick(p):
        m = re.search(p, text)
        return m.group(1).strip() if m else None

    svc = pick(r"销售服务费率\s*(---|[\d.]+%)")
    return {
        "full_name": pick(r"基金全称\s*(.+?)\s*基金简称"),
        "short_name": pick(r"基金简称\s*(.+?)\s*基金代码"),
        "fund_type": pick(r"基金类型\s*(.+?)\s*发行日期"),
        "inception": pick(r"成立日期/规模\s*(\d{4}年\d{2}月\d{2}日)"),
        "net_assets": pick(r"净资产规模\s*([\d.]+亿元)"),
        "company": pick(r"基金管理人\s*(.+?)\s*基金托管人"),
        "mgmt_fee": pick(r"管理费率\s*([\d.]+)\s*%"),
        "custody_fee": pick(r"托管费率\s*([\d.]+)\s*%"),
        "sales_service_fee": None if svc in (None, "---") else svc,
        "benchmark": pick(r"业绩比较基准\s*(.+?)\s*跟踪标的"),
        "track_index": pick(r"跟踪标的\s*(\S+?)\s*◆"),
    }


def classify(rec: dict) -> str:
    name = rec.get("short_name") or ""
    ftype = rec.get("fund_type") or ""
    bench = rec.get("benchmark") or ""
    if "QDII" in ftype or "QDII" in name:
        return "QDII黄金（境外）"
    if "股票" in ftype or "黄金股" in name or "产业股票" in bench:
        return "黄金股（股票）"
    if "上海金" in bench or "上海金" in name:
        return "上海金基准价"
    if "Au99.99" in bench or "黄金9999" in (rec.get("track_index") or ""):
        return "实物黄金Au99.99 ✅"
    if "指数型-其他" in ftype:
        return "指数型-其他（待核）"
    return "其他"


def main() -> None:
    funds = load_fund_list()
    sel = [x for x in funds if "黄金" in x[2] or "黄金" in x[4]]
    log(f"fund list {len(funds)}, 黄金相关 {len(sel)}")

    out: list[dict] = []
    for code, _pinyin, name, ftype, _full in sel:
        r = get(JBGK.format(code=code), timeout=25)
        rec = {"code": code, "name": name, "list_type": ftype}
        if r is not None:
            rec.update(parse(strip_tags(decode_bytes(r.content))))
        rec["category"] = classify(rec)
        out.append(rec)
        log(f"{code} {name[:24]:<26} {rec['category']} {rec.get('mgmt_fee') or '-'}/{rec.get('custody_fee') or '-'} {rec.get('net_assets') or '-'}")
        time.sleep(1.0)

    (DATA / "survey.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # markdown
    order = ["实物黄金Au99.99 ✅", "上海金基准价", "指数型-其他（待核）", "黄金股（股票）", "QDII黄金（境外）", "其他"]
    lines = ["# 黄金类基金全市场扫描", "", f"共 {len(out)} 只（名称含「黄金」）。数据源：天天基金基本概况页。", ""]
    for cat in order:
        rows = [r for r in out if r["category"] == cat]
        if not rows:
            continue
        lines += [f"## {cat}（{len(rows)}）", "",
                  "| 代码 | 简称 | 公司 | 管理费 | 托管费 | 销售服务费 | 规模 | 成立 | 业绩比较基准 |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda x: x["code"]):
            lines.append(
                f"| {r['code']} | {r.get('short_name') or r['name']} | {r.get('company') or '-'} "
                f"| {r.get('mgmt_fee') or '-'}% | {r.get('custody_fee') or '-'}% "
                f"| {r.get('sales_service_fee') or '—'} | {r.get('net_assets') or '-'} "
                f"| {r.get('inception') or '-'} | {(r.get('benchmark') or '-')[:40]} |"
            )
        lines.append("")
    (DATA / "survey.md").write_text("\n".join(lines), encoding="utf-8")
    log("survey -> data/survey.json, data/survey.md")


if __name__ == "__main__":
    main()
