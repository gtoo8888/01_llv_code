#!/usr/bin/env python3
"""
nightingale —— 全貌上下文合并器

把整个 skill 的全部文本内容（SKILL.md + docs/* + references/* + scripts/*）
合并为一份 NIGHTINGALE_CONTEXT.md，方便一次性拷贝给大模型理解全貌。

使用方法（在 nightingale/ 目录下执行）：
    python3 scripts/build_context.py

产物 NIGHTINGALE_CONTEXT.md 为自动生成，勿手改；
改源文件（SKILL.md / docs/ / references/ / scripts/）后重新运行本脚本即可。
"""

import os
from datetime import datetime

# 脚本位于 <skill>/scripts/，BASE 取其上一级 = skill 根目录
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_NAME = "NIGHTINGALE_CONTEXT.md"
SEP = "#" + "=" * 77
SELF_NAME = os.path.basename(__file__)


def is_md(name: str) -> bool:
    return name.endswith(".md")


def collect() -> list:
    """返回 [(显示路径, 绝对路径, 是否 markdown)]，按 入口→docs→references→scripts 顺序。"""
    out = []

    skill = os.path.join(BASE, "SKILL.md")
    if os.path.isfile(skill):
        out.append(("SKILL.md", skill, True))

    for sub in ("docs", "references", "scripts"):
        d = os.path.join(BASE, sub)
        if not os.path.isdir(d):
            continue
        names = [n for n in os.listdir(d)
                 if os.path.isfile(os.path.join(d, n)) and n != SELF_NAME]
        # markdown 优先、再按名字排（docs/ 本身已带序号）
        names.sort(key=lambda n: (0 if is_md(n) else 1, n))
        for n in names:
            out.append((f"{sub}/{n}", os.path.join(d, n), is_md(n)))

    return out


def fence(lang: str, text: str) -> str:
    return f"```{lang}\n{text}\n```"


def render(label: str, full: str, md: bool) -> str:
    with open(full, "r", encoding="utf-8") as f:
        text = f.read().strip()

    head = [SEP, f"# 文件：{label}", SEP, ""]
    if md:
        # markdown 原样拷贝（已是富文本）
        body = text
    else:
        # 代码/JSON/文本样例套代码块，保证投喂时可读
        lang = {"json": "json", "js": "javascript", "sh": "bash"}.get(
            full.rsplit(".", 1)[-1], "text")
        body = fence(lang, text)

    return "\n".join(head + [body, ""])


def main():
    files = collect()
    print(f"📋 待合并文件（共 {len(files)} 个）：")
    for label, full, _ in files:
        n = sum(1 for _ in open(full, "r", encoding="utf-8"))
        print(f"  {full}（{n} 行）")
    print()

    lines = [
        "# nightingale（夜莺）—— 全貌上下文",
        "",
        f"> 自动生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 由 scripts/{SELF_NAME} 生成",
        f"> 用途：合并 {len(files)} 个源文件为单份，方便一次性拷贝/投喂给大模型理解夜莺全貌。",
        "> 本文件为自动生成产物，勿手改；改源文件后重跑：`python3 scripts/build_context.py`",
        "",
        "---",
        "",
        "## 文件清单",
        "",
    ]
    lines += [f"- `{label}`" for label, _, _ in files]
    lines += ["", "---", ""]

    for label, full, md in files:
        lines.append(render(label, full, md))

    out_path = os.path.join(BASE, OUT_NAME)
    content = "\n".join(lines) + "\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"🔨 正在生成 {OUT_NAME}...")
    print(f"✅ 已更新：{out_path}")
    print(f"   {len(content.splitlines())} 行，{len(content)} 字符，{len(files)} 个文件")


if __name__ == "__main__":
    main()
