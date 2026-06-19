#!/usr/bin/env python3
"""DeepSeek 对话合并工具

将多个 DeepSeek 导出的 JSON 对话文件合并为一个，自动去重并按时间排序。

用法:
  conda activate llm_chat_dashboard
  python scripts/merge_conversations.py

配置:
  编辑本脚本顶部的 SOURCE_FILES 和 OUTPUT_DIR 变量。
"""

import json
from pathlib import Path
from datetime import datetime

# ============ 配置 ============
# 相对于 pro5/ 根目录的路径
SOURCE_FILES = [
    "llm_sessions/deepseek_data-2026-06-15/conversations.json",
    "llm_sessions/deepseek_data-2026-06-19/conversations.json",
]

# 合并后的输出目录（自动创建 conversations.json）
OUTPUT_DIR = "llm_sessions/deepseek_data-merged"


def project_root() -> Path:
    """定位到 pro5/ 项目根目录"""
    script_dir = Path(__file__).resolve().parent
    if (script_dir.parent / "app.py").exists():
        return script_dir.parent
    return Path.cwd()


def load_json(path: Path):
    """加载 JSON 文件，返回对话列表"""
    print(f"  📂 加载: {path.name}  ({path.stat().st_size / 1024 / 1024:.1f} MB)", end="", flush=True)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  → {len(data)} 个对话")
    return data


def main():
    root = project_root()
    start_time = datetime.now()

    print(f"\n{'='*60}")
    print(f"  DeepSeek 对话合并工具")
    print(f"{'='*60}\n")

    # 加载所有文件
    all_convs = []
    for rel_path in SOURCE_FILES:
        path = root / rel_path
        if not path.exists():
            print(f"  ❌ 文件不存在: {path}")
            continue
        all_convs.extend(load_json(path))

    if not all_convs:
        print("\n  ❌ 没有可合并的对话，退出\n")
        return

    print(f"\n  📊 合并前总数: {len(all_convs)}")

    # 去重：同 ID 保留 updated_at 更新的那条
    deduped = {}
    dup_count = 0
    for conv in all_convs:
        cid = conv.get("id", "")
        if not cid:
            continue
        if cid in deduped:
            dup_count += 1
            existing = deduped[cid]
            if conv.get("updated_at", "") > existing.get("updated_at", ""):
                deduped[cid] = conv
        else:
            deduped[cid] = conv

    # 按 inserted_at 升序排列
    sorted_convs = sorted(deduped.values(), key=lambda c: c.get("inserted_at", ""))

    print(f"  🔁 去重移除: {dup_count} 条重复")
    print(f"  ✅ 合并后总数: {len(sorted_convs)}")
    print(f"  📅 时间范围: {sorted_convs[0].get('inserted_at', '?')[:10]} → {sorted_convs[-1].get('inserted_at', '?')[:10]}")

    # 写入输出目录
    out_dir = root / OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "conversations.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sorted_convs, f, ensure_ascii=False)

    elapsed = datetime.now() - start_time
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"\n  💾 写入: {OUTPUT_DIR}/conversations.json  ({size_mb:.1f} MB)")
    print(f"  ⏱  耗时: {elapsed.total_seconds():.1f} 秒\n")

    # 提示修改 JSON_FILE
    print(f"  💡 在 deepseek_parser.py 中将 JSON_FILE 改为:")
    print(f'     JSON_FILE = "{OUTPUT_DIR}/conversations.json"')
    print()


if __name__ == "__main__":
    main()
