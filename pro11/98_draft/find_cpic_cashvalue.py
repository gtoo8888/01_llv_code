# -*- coding: utf-8 -*-
"""一次性脚本：在太保官网的产品信息披露列表里找“金生无忧2025（成人版）”的三个附件链接。

列表页是静态 HTML（GBK 编码），每个产品一行，附件链接形如：
    /mpdfjs/pdf.html?file=/upload/resources/file/2023/06/21/72195.pdf
其中“现金价值全表”就是我们要的那份。

用法：
    python 98_draft/find_cpic_cashvalue.py
"""

import re
import sys
import urllib.request

BASE = ("http://life.cpic.com.cn/xrsbx/gkxxpl/jbxx/gsgk/jydbxcpmljtk/"
        "{section}/{category}/index{page}.shtml")
KEY = "金生无忧2025"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

ANCHOR_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{0,80})</a>')


def fetch(section: str, category: str, page: int) -> str:
    suffix = "" if page == 1 else f"_{page}"
    url = BASE.format(section=section, category=category, page=suffix)
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("gb18030", errors="ignore")


def main() -> int:
    found = False
    for section in ("zbcp", "tbcp"):          # 在售 / 停售
        for category in ("jkx", "sx", "yx", "yix"):   # 健康险 / 寿险 / 意外 …
            for page in range(1, 41):
                try:
                    html = fetch(section, category, page)
                except Exception:
                    break          # 该目录没有更多页
                links = ANCHOR_RE.findall(html)
                hits = [(href, text.strip()) for href, text in links if KEY in text]
                if not hits:
                    continue
                found = True
                print(f"=== {section}/{category} 第 {page} 页命中 {len(hits)} 条 ===")
                for href, text in hits:
                    print(f"  {text}\n    {href}")

    if not found:
        print("没有找到，可能不在这些目录里")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
