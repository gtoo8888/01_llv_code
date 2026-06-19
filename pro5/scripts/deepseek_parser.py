#!/usr/bin/env python3
"""DeepSeek 对话数据解析工具

解析 DeepSeek 官方导出的 JSON 对话文件，支持浏览、查看、导出对话知识库。

用法:
  conda activate llm_chat_dashboard
  python scripts/deepseek_parser.py list                列出所有对话
  python scripts/deepseek_parser.py view <索引号或ID>   查看单个对话详情
  python scripts/deepseek_parser.py export [参数]       导出对话为 Markdown
  python scripts/deepseek_parser.py status              查看对话库概览
"""

import json
import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# ==== 日志配置 ====
logger = logging.getLogger("deepseek")
logger.setLevel(logging.INFO)
_log_dir = Path(__file__).resolve().parent
_log_handler_screen = logging.StreamHandler(sys.stderr)
_log_handler_screen.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_log_handler_screen)
_log_handler_file = logging.FileHandler(str(_log_dir / "deepseek_parser.log"), encoding="utf-8")
_log_handler_file.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_log_handler_file)

# ============ 配置 ============
# 相对于 pro5/ 根目录的路径
# JSON_FILE = "llm_sessions/deepseek_data-2026-03-14/conversations.json"
# JSON_FILE = "llm_sessions/deepseek_data-2026-06-19/conversations.json"
JSON_FILE = "llm_sessions/deepseek_data-merged/conversations.json"

# 输出目录由输入文件夹名自动推导：
JSON_DIR = Path(JSON_FILE).parent
OUTPUT_DIR = "llm_conversation_archives/" + JSON_DIR.name

# 导出缓存：批量导出时先缓存在内存，最后统一写盘
_export_cache = {}  # str(month_dir) -> (Path, [conv_data, ...])


def _fmt_dt(ts: str, fmt: str) -> str:
    """安全格式化 ISO 时间字符串，避免硬编码切片"""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime(fmt)
    except (ValueError, TypeError):
        return ""


def project_root() -> Path:
    """定位到 pro5/ 项目根目录（脚本可能在 pro5/scripts/ 下运行）"""
    # 尝试从脚本所在目录往上找
    script_dir = Path(__file__).resolve().parent  # .../pro5/scripts/
    if (script_dir.parent / "app.py").exists():
        return script_dir.parent
    # 尝试从 CWD
    cwd = Path.cwd()
    if (cwd / "app.py").exists():
        return cwd
    if (cwd / "scripts" / "deepseek_parser.py").exists():
        return cwd
    return cwd


def load_conversations(root: Path):
    """加载 JSON 文件，返回对话列表。使用流式读取部分数据优化大文件加载。"""
    path = root / JSON_FILE
    if not path.exists():
        logger.error(f"❌ 文件不存在: {path}")
        sys.exit(1)

    size_mb = path.stat().st_size / 1024 / 1024
    logger.info(f"📂 加载文件 ({size_mb:.1f} MB)...")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"\n❌ JSON 解析失败: {e}")
        logger.error(f"   文件可能已损坏，请检查: {path.name}")
        sys.exit(1)

    if not isinstance(data, list):
        logger.error(f"❌ 期望 JSON 数组，但得到 {type(data).__name__}")
        sys.exit(1)

    logger.info(f"✅ {len(data)} 个对话")
    return data


def linearize_messages(conv: dict) -> list:
    """
    将 mapping 树结构遍历为有序的消息列表。
    从 root 开始，按 children 顺序深度优先遍历。
    """
    mapping = conv.get("mapping", {})
    messages = []

    def walk(node_id: str):
        node = mapping.get(node_id)
        if not node:
            return
        msg_data = node.get("message")
        if msg_data:
            messages.append({"id": node_id, **msg_data})
        for child_id in node.get("children", []):
            walk(child_id)

    walk("root")
    return messages


def summarize_conversation(conv: dict, msgs: list = None) -> dict:
    """提取对话的摘要信息（传入 msgs 可跳过内部遍历）"""
    if msgs is None:
        msgs = linearize_messages(conv)
    models = sorted(set(m.get("model", "") for m in msgs if m.get("model")))
    user_msgs = sum(1 for m in msgs if any(
        f.get("type") == "REQUEST" for f in m.get("fragments", [])
    ))
    return {
        "id": conv.get("id", "???"),
        "title": conv.get("title", "(无标题)"),
        "inserted_at": conv.get("inserted_at", ""),
        "updated_at": conv.get("updated_at", ""),
        "total_msgs": len(msgs),
        "user_msgs": user_msgs,
        "models": models,
    }


def cmd_status(conversations: list):
    """输出对话库整体概览"""
    total = len(conversations)
    total_msgs = 0
    total_user = 0
    models = set()
    months = {}  # key: "2025_01"
    earliest = None
    latest = None

    for conv in conversations:
        s = summarize_conversation(conv)
        total_msgs += s["total_msgs"]
        total_user += s["user_msgs"]
        models.update(s["models"])

        if s["inserted_at"] and len(s["inserted_at"]) >= 7:
            month_key = _fmt_dt(s["inserted_at"], "%Y_%m") or "?"
        else:
            month_key = "?"
        months[month_key] = months.get(month_key, 0) + 1

        if s["inserted_at"]:
            if earliest is None or s["inserted_at"] < earliest:
                earliest = s["inserted_at"]
            if latest is None or s["inserted_at"] > latest:
                latest = s["inserted_at"]

    logger.info(f"{'='*60}")
    logger.info(f"  DeepSeek 对话知识库 - 概览")
    logger.info(f"{'='*60}\n")

    logger.info(f"  📊 对话总数:       {total}")
    logger.info(f"  💬 消息总数:       {total_msgs}（用户 {total_user} 条）")
    logger.info(f"  📅 时间跨度:       {earliest[:10] if earliest else '?'} → {latest[:10] if latest else '?'}")
    logger.info(f"  🤖 使用的模型:     {', '.join(sorted(models))}")

    max_bar = max(months.values()) if months else 1
    logger.info(f"\n  {'─'*56}")
    logger.info(f"  月度分布:")
    for mk in sorted(months.keys()):
        cnt = months[mk]
        bar_len = int(cnt / max_bar * 30) or 1
        bar = "█" * bar_len
        logger.info(f"    {mk}: {bar} ({cnt})")
    logger.info("")


def cmd_list(conversations: list):
    """列出所有对话的摘要"""
    logger.info(f"\n{'='*70}")
    logger.info(f"  DeepSeek 对话知识库 — 共 {len(conversations)} 个对话")
    logger.info(f"{'='*70}\n")

    for i, conv in enumerate(conversations, 1):
        s = summarize_conversation(conv)
        model_str = ", ".join(s["models"]) if s["models"] else "-"
        date_str = _fmt_dt(s["inserted_at"], "%Y-%m-%dT%H:%M:%S") or "?"
        title = s["title"]
        if len(title) > 50:
            title = title[:47] + "..."

        logger.info(f"  [{i:3d}] {title}")
        logger.info(f"        ID: {s['id']}")
        logger.info(f"        日期: {date_str}  |  消息: {s['total_msgs']} 条 (用户 {s['user_msgs']} 条)  |  模型: {model_str}")
        logger.info("")

def cmd_view(conversations: list, target: str):
    """查看单个对话的完整内容"""
    conv = _find_conversation(conversations, target)
    if not conv:
        logger.error(f"❌ 未找到匹配的对话: {target}")
        sys.exit(1)

    msgs = linearize_messages(conv)
    s = summarize_conversation(conv, msgs)

    logger.info(f"\n{'='*70}")
    logger.info(f"  {s['title']}")
    logger.info(f"  ID: {s['id']}  |  {_fmt_dt(s['inserted_at'], '%Y-%m-%dT%H:%M:%S')} → {_fmt_dt(s['updated_at'], '%Y-%m-%dT%H:%M:%S')}")
    logger.info(f"  消息: {s['total_msgs']} 条  |  模型: {', '.join(s['models'])}")
    logger.info(f"{'='*70}\n")

    for i, m in enumerate(msgs, 1):
        role = "用户" if _is_user_message(m) else "Assistant"
        model = m.get("model", "")
        ts = _fmt_dt(m.get("inserted_at", ""), "%Y-%m-%dT%H:%M:%S")

        # 分隔线
        logger.info(f"{'─'*60}")
        logger.info(f"  [{i}] {role}  |  {model}  |  {ts}")
        logger.info(f"{'─'*60}")

        for frag in m.get("fragments", []):
            ftype = frag.get("type", "")
            content = frag.get("content", "")

            if ftype == "REQUEST":
                logger.info(f"\n{content}\n")
            elif ftype == "THINK":
                if content.strip():
                    # 用 dim 风格的 ░ 标记 thinking
                    logger.info(f"\n── 思考过程 ──\n{content}\n")
            elif ftype == "RESPONSE":
                logger.info(f"\n{content}\n")

    logger.info(f"{'='*70}")


def _export_one(conv: dict, out_dir: Path):
    """导出单个对话到 Markdown 文件（_data.json 和 _index.md 延迟写盘）"""
    msgs = linearize_messages(conv)
    s = summarize_conversation(conv, msgs)

    # 按年/月层级目录: 2025/01/  2025/02/  ...
    if s["inserted_at"] and len(s["inserted_at"]) >= 7:
        year_dir = out_dir / _fmt_dt(s["inserted_at"], "%Y")
        month_num = int(_fmt_dt(s["inserted_at"], "%m"))
        month_name = MONTH_NAMES[month_num] if 1 <= month_num <= 12 else ""
        month_label = f"{_fmt_dt(s['inserted_at'], '%m')}_{month_name}" if month_name else _fmt_dt(s["inserted_at"], "%m")
        month_dir = year_dir / month_label
    else:
        month_dir = out_dir / "unknown"
    month_dir.mkdir(parents=True, exist_ok=True)

    # 文件名: 日期_标题.md
    date_prefix = _fmt_dt(s["inserted_at"], "%Y-%m-%d") or "unknown"
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in s["title"])
    safe_title = safe_title.strip()[:60] or "untitled"
    filename = f"{date_prefix}_{safe_title}.md"
    filepath = month_dir / filename

    lines = [
        f"# {s['title']}\n",
        f"\n> **ID:** `{s['id']}`\n",
        f"> **时间:** {_fmt_dt(s['inserted_at'], '%Y-%m-%dT%H:%M:%S')} → {_fmt_dt(s['updated_at'], '%Y-%m-%dT%H:%M:%S')}\n",
        f"> **消息:** {s['total_msgs']} 条 | **模型:** {', '.join(s['models'])}\n",
        "\n---\n",
    ]

    for m in msgs:
        role = "🤖 **Assistant**" if not _is_user_message(m) else "👤 **User**"
        model = m.get("model", "")
        ts = _fmt_dt(m.get("inserted_at", ""), "%Y-%m-%dT%H:%M:%S")

        lines.append(f"\n### {role} | {model} | {ts}\n")

        for frag in m.get("fragments", []):
            ftype = frag.get("type", "")
            content = frag.get("content", "")

            if ftype == "REQUEST":
                lines.append(f"\n{content}\n")
            elif ftype == "THINK" and content.strip():
                lines.append(f"\n<details>\n<summary>💭 思考过程</summary>\n\n{content}\n\n</details>\n")
            elif ftype == "RESPONSE":
                lines.append(f"\n{content}\n")

        lines.append("\n---\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # 缓存结构化数据（延迟写盘）
    conv_data = _build_conv_data(conv, s, msgs)
    month_key = str(month_dir)
    if month_key not in _export_cache:
        _export_cache[month_key] = (month_dir, [])
    _export_cache[month_key][1].append(conv_data)

    logger.info(f"  ✅ {filename}  ({s['total_msgs']} 条消息)")
    return filename


def _build_month_index(month_dir: Path, convs: list = None):
    """重建 _index.md（传入 convs 可跳过从磁盘读取）"""
    index_path = month_dir / "_index.md"

    if convs is None:
        data_path = month_dir / "_data.json"
        if not data_path.exists():
            # 无 _data.json 时退化：按文件名列出
            files = sorted(month_dir.glob("*.md"))
            files = [f for f in files if f.name != "_index.md"]
            lines = ["# 月度对话索引\n", f"\n共 {len(files)} 个对话\n", "\n---\n"]
            for f in files:
                first_line = (f.read_text(encoding="utf-8").split("\n") or [""])[0]
                title = first_line.lstrip("# ").strip() or f.stem
                date_part = f.name[:10] if len(f.name) >= 10 else ""
                lines.append(f"- [{title}]({f.name})  _{date_part}_\n")
            index_path.write_text("".join(lines), encoding="utf-8")
            return

        try:
            with open(data_path, "r", encoding="utf-8") as f:
                convs = json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"  \u26a0\ufe0f {data_path.name} \u89e3\u6790\u5931\u8d25\uff0c\u56de\u9000\u5230\u6587\u4ef6\u5217\u8868\u6a21\u5f0f")
            convs = []

    if not convs:
        index_path.write_text("# 月度对话索引\n\n（本月无对话记录）\n", encoding="utf-8")
        return

    stats = _compute_month_stats(convs)
    markdown = _render_month_index(convs, stats)
    index_path.write_text(markdown, encoding="utf-8")
def _compute_month_stats(convs: list) -> dict:
    """计算月度统计，返回字典供渲染使用"""
    total_msgs = sum(c["message_count"] for c in convs)
    total_user = sum(c["user_message_count"] for c in convs)

    model_stats = {}
    has_think_count = 0
    total_request_chars = 0
    total_response_chars = 0

    for c in convs:
        for m in c.get("models", []):
            model_stats[m] = model_stats.get(m, 0) + 1
        for msg in c.get("messages", []):
            if msg.get("has_thinking"):
                has_think_count += 1
            total_request_chars += msg.get("request_length", 0)
            total_response_chars += msg.get("response_length", 0)

    first_date = _fmt_dt(convs[0]["inserted_at"], "%Y-%m-%d")
    last_date = _fmt_dt(convs[-1]["inserted_at"], "%Y-%m-%d")
    year = _fmt_dt(convs[0]["inserted_at"], "%Y")
    month_num = int(_fmt_dt(convs[0]["inserted_at"], "%m"))
    month_name = MONTH_NAMES[month_num] if 1 <= month_num <= 12 else ""

    day_counts = {}
    for c in convs:
        d = _fmt_dt(c["inserted_at"], "%Y-%m-%d") or "unknown"
        day_counts[d] = day_counts.get(d, 0) + 1

    return {
        "total_msgs": total_msgs,
        "total_user": total_user,
        "total_assistant": total_msgs - total_user,
        "model_stats": model_stats,
        "has_think_count": has_think_count,
        "total_request_chars": total_request_chars,
        "total_response_chars": total_response_chars,
        "first_date": first_date,
        "last_date": last_date,
        "year": year,
        "month_num": month_num,
        "month_name": month_name,
        "day_counts": day_counts,
        "max_day": max(day_counts.values()) if day_counts else 1,
        "model_str": " · ".join(f"{k}({v})" for k, v in sorted(model_stats.items())),
    }


def _render_month_index(convs: list, stats: dict) -> str:
    """从统计数据渲染 _index.md 的完整文本"""
    lines = [
        f"# 月度对话索引 — {stats['year']}年{stats['month_num']}月 ({stats['month_name']})\n",
        f"\n## 📊 统计概览\n",
        f"\n| 指标 | 数值 |\n",
        f"|------|------|\n",
        f"| 对话总数 | {len(convs)} |\n",
        f"| 消息总数 | {stats['total_msgs']}（用户 {stats['total_user']} · Assistant {stats['total_assistant']}） |\n",
        f"| 时间跨度 | {stats['first_date']} → {stats['last_date']} |\n",
        f"| 涉及模型 | {stats['model_str']} |\n",
        f"| 含思考过程 | {stats['has_think_count']} 条消息 |\n",
        f"| 输入总字符 | ~{stats['total_request_chars']:,} |\n",
        f"| 输出总字符 | ~{stats['total_response_chars']:,} |\n",
        "\n---\n",
        "\n## 📅 每日对话量\n",
    ]

    for day in sorted(stats["day_counts"].keys()):
        cnt = stats["day_counts"][day]
        bar_len = int(cnt / stats["max_day"] * 20) or 1
        lines.append(f"\n  {day[-2:]}日: {'█' * bar_len} ({cnt})")
    lines.append("\n\n---\n")

    lines.append("\n## 📋 对话清单\n")

    for c in convs:
        title = c["title"]
        date_prefix = _fmt_dt(c["inserted_at"], "%Y-%m-%d") or "unknown"
        safe_title = "".join(ch if ch.isalnum() or ch in " _-" else "_" for ch in title)
        safe_title = safe_title.strip()[:60] or "untitled"
        filename = f"{date_prefix}_{safe_title}.md"

        c_models = " / ".join(c.get("models", []))
        has_r1 = any("reasoner" in m for m in c.get("models", []))
        r1_tag = " 💭" if has_r1 else ""
        c_msgs = c["message_count"]

        lines.append(f"\n- **[{{title}}]({{filename}})**  _{{date_prefix}}_  ·  {{c_msgs}} 条消息  ·  {{c_models}}{{r1_tag}}".format(
            title=title, filename=filename, date_prefix=date_prefix,
            c_msgs=c_msgs, c_models=c_models, r1_tag=r1_tag,
        ))

    return "".join(lines)


def _build_conv_data(conv: dict, s: dict, msgs: list) -> dict:
    """构建单个对话的结构化 JSON 条目"""
    messages = []
    for m in msgs:
        is_user = _is_user_message(m)
        entry = {
            "role": "user" if is_user else "assistant",
            "model": m.get("model", ""),
            "inserted_at": m.get("inserted_at", ""),
        }
        for frag in m.get("fragments", []):
            ftype = frag.get("type", "")
            content = frag.get("content", "")
            if ftype == "REQUEST":
                entry["request_length"] = len(content)
            elif ftype == "THINK":
                has = bool(content.strip())
                entry["has_thinking"] = has
                entry["thinking_length"] = len(content) if has else 0
            elif ftype == "RESPONSE":
                entry["response_length"] = len(content)
        messages.append(entry)

    return {
        "id": conv.get("id", ""),
        "title": s["title"],
        "inserted_at": s["inserted_at"],
        "updated_at": s["updated_at"],
        "message_count": s["total_msgs"],
        "user_message_count": s["user_msgs"],
        "models": s["models"],
        "messages": messages,
    }


def _update_month_data(month_dir: Path, conv_data: dict):
    """在 _data.json 中添加/更新一条对话的结构化数据"""
    data_path = month_dir / "_data.json"

    if data_path.exists():
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    else:
        data = []

    conv_id = conv_data["id"]
    for i, entry in enumerate(data):
        if entry["id"] == conv_id:
            data[i] = conv_data
            break
    else:
        data.append(conv_data)

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cmd_export(conversations: list, target: str = None, top: int = None):
    """导出对话为 Markdown 文件"""
    start_time = datetime.now()
    root = project_root()
    out_dir = root / OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    if top is not None:
        # 导出前 N 条
        selected = conversations[:top]
        logger.info(f"导出前 {top} 个对话...\n")
        for i, conv in enumerate(selected, 1):
            _export_one(conv, out_dir)
        count = len(selected)
    elif target:
        # 导出单个对话
        conv = _find_conversation(conversations, target)
        if not conv:
            logger.info(f"❌ 未找到匹配的对话: {target}")
            sys.exit(1)
        _export_one(conv, out_dir)
        count = 1
    else:
        # 导出全部对话
        print(f"即将导出 {len(conversations)} 个对话，确认？(y/N): ", end="", flush=True)
        confirm = sys.stdin.readline().strip().lower()
        if confirm != "y":
            logger.info("❌ 已取消")
            return
        for i, conv in enumerate(conversations, 1):
            _export_one(conv, out_dir)
        count = len(conversations)

    # 统一写盘：_data.json 和 _index.md
    _flush_export_cache()

    # 根目录归档索引
    _build_archive_index(out_dir)

    elapsed = datetime.now() - start_time
    secs = elapsed.total_seconds()
    if secs < 60:
        time_str = f"{secs:.1f} 秒"
    else:
        time_str = f"{int(secs // 60)} 分 {secs % 60:.1f} 秒"
    logger.info(f"\n⏱  耗时: {time_str}  |  📁 共 {count} 个文件, 保存在: {OUTPUT_DIR}/")


MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]


def _flush_export_cache():
    """将所有缓存写入磁盘：_data.json + _index.md"""
    for month_key, (month_dir, entries) in _export_cache.items():
        # 合并已有磁盘数据和本次新增
        data_path = month_dir / "_data.json"
        if data_path.exists():
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
        else:
            existing = []

        # 去重（同 ID 覆盖）
        by_id = {e["id"]: e for e in existing}
        for e in entries:
            by_id[e["id"]] = e
        merged = list(by_id.values())

        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        # 重建索引
        _build_month_index(month_dir, merged)

    _export_cache.clear()


def _build_archive_index(out_dir: Path):
    """在导出根目录生成 _index.md，汇总全库统计"""
    index_path = out_dir / "_index.md"

    # 收集所有月份目录下的 _data.json
    data_files = sorted(out_dir.rglob("_data.json"))

    if not data_files:
        index_path.write_text("# 对话归档\n\n暂无数据。\n", encoding="utf-8")
        return

    total_convs = 0
    total_msgs = 0
    total_user = 0
    model_stats = {}
    think_count = 0
    total_request_chars = 0
    total_response_chars = 0
    yearly = {}   # year -> {convs, msgs, user, models}
    monthly = {}  # "2025/01_January" -> {convs, msgs, user, models}
    earliest = None
    latest = None

    for dp in data_files:
        try:
            with open(dp, "r", encoding="utf-8") as f:
                convs = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        # 路径推断
        year = dp.parent.parent.name if dp.parent.parent != dp.parent else "?"
        rel = dp.parent.relative_to(out_dir)
        month_key = str(rel)

        if year not in yearly:
            yearly[year] = {"convs": 0, "msgs": 0, "user": 0, "models": {}}
        if month_key not in monthly:
            monthly[month_key] = {"convs": 0, "msgs": 0, "user": 0, "models": {}}

        for c in convs:
            total_convs += 1
            total_msgs += c["message_count"]
            total_user += c["user_message_count"]

            yearly[year]["convs"] += 1
            yearly[year]["msgs"] += c["message_count"]
            yearly[year]["user"] += c["user_message_count"]

            monthly[month_key]["convs"] += 1
            monthly[month_key]["msgs"] += c["message_count"]
            monthly[month_key]["user"] += c["user_message_count"]

            for m in c.get("models", []):
                model_stats[m] = model_stats.get(m, 0) + 1
                yearly[year]["models"][m] = yearly[year]["models"].get(m, 0) + 1
                monthly[month_key]["models"][m] = monthly[month_key]["models"].get(m, 0) + 1

            for msg in c.get("messages", []):
                if msg.get("has_thinking"):
                    think_count += 1
                total_request_chars += msg.get("request_length", 0)
                total_response_chars += msg.get("response_length", 0)

            if c["inserted_at"]:
                if earliest is None or c["inserted_at"] < earliest:
                    earliest = c["inserted_at"]
                if latest is None or c["inserted_at"] > latest:
                    latest = c["inserted_at"]
    total_assistant = total_msgs - total_user
    model_str = " · ".join(f"{k}({v})" for k, v in sorted(model_stats.items()))

    lines = [
        f"# 📚 对话归档总览\n",
        f"\n> **数据源:** `{Path(JSON_FILE).name if JSON_FILE else '?'}`\n",
        f"> **生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"> **时间跨度:** {_fmt_dt(earliest, '%Y-%m-%d') or '?'} → {_fmt_dt(latest, '%Y-%m-%d') or '?'}\n",
        "\n---\n",
        "\n## 📊 全局统计\n",
        f"\n| 指标 | 数值 |\n",
        f"|------|------|\n",
        f"| 对话总数 | {total_convs} |\n",
        f"| 消息总数 | {total_msgs}（用户 {total_user} · Assistant {total_assistant}） |\n",
        f"| 涉及模型 | {model_str} |\n",
        f"| 含思考过程 | {think_count} 条消息 |\n",
        f"| 输入总字符 | ~{total_request_chars:,} |\n",
        f"| 输出总字符 | ~{total_response_chars:,} |\n",
        "\n---\n",
        "\n## 📅 月度统计\n",
        "\n| 月份 | 对话 | 消息 | 模型 |\n",
        "|------|------|------|------|\n",
    ]

    for year in sorted(yearly.keys()):
        y = yearly[year]
        ym = " · ".join(f"{k}({v})" for k, v in sorted(y["models"].items()))
        lines.append(f"| {year} **合计** | {y['convs']} | {y['msgs']}（用户 {y['user']}） | {ym} |\n")

    for key in sorted(monthly.keys()):
        m = monthly[key]
        mm = " · ".join(f"{k}({v})" for k, v in sorted(m["models"].items()))
        lines.append(f"| {key} | {m['convs']} | {m['msgs']}（用户 {m['user']}） | {mm} |\n")

    lines.append("\n---\n")

    # 按月目录链接
    lines.append("\n## 📁 目录结构\n")
    for dp in data_files:
        rel = dp.relative_to(out_dir).parent
        lines.append(f"- [{rel}]({rel}/)\n")

    index_path.write_text("".join(lines), encoding="utf-8")
    logger.info(f"  📋 归档索引: {index_path.relative_to(out_dir.parent.parent)}")



def _is_user_message(msg: dict) -> bool:
    """判断消息是否来自用户（包含 REQUEST 片段）"""
    for frag in msg.get("fragments", []):
        if frag.get("type") == "REQUEST":
            return True
    return False


def _find_conversation(conversations: list, target: str):
    """按索引号或 ID 前缀查找对话"""
    # 先按索引号
    try:
        idx = int(target)
        if 1 <= idx <= len(conversations):
            return conversations[idx - 1]
    except ValueError:
        pass

    # 再按 ID 前缀匹配
    matches = [c for c in conversations if c.get("id", "").startswith(target)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        logger.info(f"⚠️ 多个对话匹配 '{target}'，请使用更长的 ID 前缀:")
        for m in matches:
            logger.info(f"   {m['id']}  {m.get('title', '')}")
        return None

    return None


def build_parser():
    """构建 argparse 参数解析器"""
    import argparse

    parser = argparse.ArgumentParser(
        description="DeepSeek 对话数据解析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""使用示例:
  python scripts/deepseek_parser.py list
  python scripts/deepseek_parser.py view 1
  python scripts/deepseek_parser.py view c26ef77a
  python scripts/deepseek_parser.py export 1
  python scripts/deepseek_parser.py export --top 10
  python scripts/deepseek_parser.py export
  python scripts/deepseek_parser.py status""",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="")

    # list
    subparsers.add_parser("list", help="列出所有对话")

    # view
    p_view = subparsers.add_parser("view", help="查看单个对话详情")
    p_view.add_argument("target", help="索引号或 ID 前缀")

    # export
    p_export = subparsers.add_parser("export", help="导出对话为 Markdown")
    p_export.add_argument("target", nargs="?", default=None,
                          help="索引号或 ID 前缀（不指定则导出全部）")
    p_export.add_argument("--top", type=int, default=None,
                          help="导出前 N 条对话")

    # status
    subparsers.add_parser("status", help="查看对话库概览")

    return parser


def main():
    root = project_root()
    parser = build_parser()

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    conversations = load_conversations(root)

    if args.command == "list":
        cmd_list(conversations)
    elif args.command == "view":
        cmd_view(conversations, args.target)
    elif args.command == "export":
        cmd_export(conversations, args.target, args.top)
    elif args.command == "status":
        cmd_status(conversations)


if __name__ == "__main__":
    main()
