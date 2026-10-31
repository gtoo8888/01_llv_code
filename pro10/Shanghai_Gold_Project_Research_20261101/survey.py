"""pro11 — 上海金 ETF 调研（与 pro10 黄金 Au99.99 分开）

复用 pro10/lib 的抓取与解析能力，但数据、配置、产物完全独立。

上海金 = 上海黄金交易所「上海金集中定价合约」(SHAU)，每日 10:15 / 14:15 两次定盘，
不是 Au99.99 的连续报价。两者跟踪标的、估值方式不同，故单独成册。

用法：
    python survey.py          # 扫描上海金全市场
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRO10 = HERE.parent / "pro10"
sys.path.insert(0, str(PRO10))
sys.path.insert(0, str(HERE))

from lib.common import decode_bytes, get, strip_tags  # noqa: E402

DATA = HERE / "data"
DATA.mkdir(parents=True, exist_ok=True)

LIST_URL = "http://fund.eastmoney.com/js/fundcode_search.js"
JBGK = "https://fundf10.eastmoney.com/jbgk_{code}.html"
JJFL = "https://fundf10.eastmoney.com/jjfl_{code}.html"

# 上海金相关：名称含「上海金」或「金ETF」但不含「黄金ETF」「黄金股」
def is_shanghai_gold(name: str, ftype: str = "") -> bool:
    if "货币" in ftype or "债券" in ftype or "混合" in ftype:
        return False
    if "黄金股" in name or "产业股票" in name:
        return False
    if "上海金" in name:
        return True
    if "金ETF" in name and "黄金" not in name:
        return True
    return False


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_jbgk(text: str) -> dict:
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
        "custodian": pick(r"基金托管人\s*(.+?)\s*基金经理"),
        "mgmt_fee": pick(r"管理费率\s*([\d.]+)\s*%"),
        "custody_fee": pick(r"托管费率\s*([\d.]+)\s*%"),
        "sales_service_fee": None if svc in (None, "---") else svc,
        "benchmark": pick(r"业绩比较基准\s*(.+?)\s*跟踪标的"),
        "track_index": pick(r"跟踪标的\s*(\S+?)\s*◆"),
    }


def main() -> None:
    r = get(LIST_URL, timeout=40)
    text = decode_bytes(r.content)
    funds = json.loads(text[text.find("[[") : text.rfind("]]") + 2])
    sel = [x for x in funds if is_shanghai_gold(x[2], x[3])]
    log(f"上海金相关：{len(sel)} 只")

    out = []
    for code, _py, name, ftype, _full in sel:
        rec = {"code": code, "name": name, "list_type": ftype}
        r1 = get(JBGK.format(code=code), timeout=25)
        if r1 is not None:
            rec.update(parse_jbgk(strip_tags(decode_bytes(r1.content))))
        out.append(rec)
        log(f"{code} {name[:26]:<28} {rec.get('mgmt_fee') or '-'}/{rec.get('custody_fee') or '-'} {rec.get('net_assets') or '-'}")
        time.sleep(1.0)

    (DATA / "shanghai_gold.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = ["# 上海金 ETF 全市场扫描", "", f"共 {len(out)} 只。数据源：天天基金基本概况页。",
             "跟踪标的：上海黄金交易所「上海金集中定价合约」(SHAU)，每日两次定盘。", "",
             "| 代码 | 简称 | 公司 | 管理费 | 托管费 | 销售服务费 | 规模 | 成立 | 业绩比较基准 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for rec in sorted(out, key=lambda x: x["code"]):
        lines.append(
            f"| {rec['code']} | {rec.get('short_name') or rec['name']} | {rec.get('company') or '-'} "
            f"| {rec.get('mgmt_fee') or '-'}% | {rec.get('custody_fee') or '-'}% "
            f"| {rec.get('sales_service_fee') or '—'} | {rec.get('net_assets') or '-'} "
            f"| {rec.get('inception') or '-'} | {(rec.get('benchmark') or '-')[:38]} |"
        )
    (DATA / "shanghai_gold.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("-> data/shanghai_gold.json, data/shanghai_gold.md")


if __name__ == "__main__":
    main()
