"""
JSONL 解析逻辑
"""
import json
import re
from datetime import datetime
from pathlib import Path

from src.config import DB_PATH, SOURCE_DIR
from src.database import get_conn


def strip_user_metadata(content: str) -> str:
    """
    删除时间戳行及其之前的所有内容，保留该行中时间戳之后的部分及后续行。
    时间戳格式示例：[Thu 2026-04-02 01:02 GMT+8]
    """
    if not content:
        return content

    pattern = re.compile(r'^\s*\[.*?\d{4}.*?\](.*)$')
    lines = content.split('\n')

    for i, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            after_timestamp = match.group(1).lstrip()
            after_lines = lines[i+1:]
            if after_lines:
                new_text = after_timestamp + '\n' + '\n'.join(after_lines)
            else:
                new_text = after_timestamp
            return new_text.strip()

    return content


def extract_content_detail(content_list):
    """从 message.content 数组中提取各类内容"""
    readable_parts = []
    thinking_parts = []
    tool_calls = []

    if not content_list:
        return "", "", []

    for item in content_list:
        item_type = item.get("type", "")

        if item_type == "text":
            readable_parts.append(item.get("text", ""))

        elif item_type == "thinking":
            thinking_parts.append(item.get("thinking", ""))

        elif item_type == "toolCall":
            tool_calls.append({
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "arguments": item.get("arguments", {}),
            })

    return "\n".join(readable_parts), "\n".join(thinking_parts), tool_calls


def scan_and_parse():
    """扫描源目录，解析新文件（增量）"""
    if not SOURCE_DIR.exists():
        return

    conn = get_conn()
    c = conn.cursor()

    # 找出已解析过的文件
    c.execute("SELECT file_path FROM parsed_files")
    parsed = {row[0] for row in c.fetchall()}

    jsonl_files = [f for f in SOURCE_DIR.glob("*") if ".jsonl" in f.name and f.is_file()]
    new_files = [f for f in jsonl_files if str(f) not in parsed]

    for file_path in new_files:
        _parse_file(c, file_path)
        c.execute(
            "INSERT OR REPLACE INTO parsed_files (file_path, parsed_at) VALUES (?, ?)",
            (str(file_path), datetime.now().isoformat())
        )

    conn.commit()
    conn.close()


def _parse_file(c, file_path: Path):
    """解析单个 JSONL 文件"""
    sessions = {}  # session_key -> info
    current_session_key = None  # 当前活跃的 session
    tool_call_results = {}  # tool_call_id -> result content

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type", "")
            event_id = event.get("id", "")
            parent_id = event.get("parentId")
            timestamp = event.get("timestamp", "")

            # session 事件
            if event_type == "session":
                sk = event.get("id", "")
                current_session_key = sk
                sessions[sk] = {
                    "session_key": sk,
                    "start_time": timestamp,
                    "cwd": event.get("cwd", ""),
                    "channel": "",
                }
                c.execute(
                    "INSERT OR REPLACE INTO sessions (session_key, start_time, cwd, channel) VALUES (?, ?, ?, ?)",
                    (sk, timestamp, event.get("cwd", ""), "")
                )
                continue

            # toolResult 独立消息，暂存结果
            if event_type == "message":
                msg = event.get("message", {})
                if msg.get("role") == "tool":
                    for item in msg.get("content", []):
                        if item.get("type") == "toolResult":
                            content = item.get("content", "")
                            if isinstance(content, list):
                                for r in content:
                                    if isinstance(r, dict) and r.get("type") == "text":
                                        content = r.get("text", "")
                            tool_call_results[parent_id] = str(content)[:5000]
                    continue  # 只跳过 tool 消息，不跳过其他 message

            # 只处理 message 类型（非 message 事件跳过）
            if event_type != "message":
                continue

            msg = event.get("message", {})
            role = msg.get("role", "")
            content_list = msg.get("content", [])
            usage = msg.get("usage", {})
            model = msg.get("model", "")
            provider = msg.get("provider", "")
            api = msg.get("api", "")
            stop_reason = msg.get("stopReason", "")

            readable_text, thinking_text, tool_calls_list = extract_content_detail(content_list)

            channel = api or provider or ""
            if not channel and role == "user" and readable_text.startswith("System:"):
                m = re.search(r'\[([\w-]+)\[', readable_text)
                if m:
                    channel = m.group(1)

            sk = current_session_key or "unknown"

            c.execute("""
                INSERT OR REPLACE INTO messages
                (id, session_key, parent_id, role, content, thinking, timestamp,
                 model, provider, channel, tokens_input, tokens_output, tokens_total,
                 stop_reason, has_tool_calls)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, sk, parent_id, role, readable_text, thinking_text,
                timestamp, model, provider, channel,
                usage.get("input", 0), usage.get("output", 0), usage.get("totalTokens", 0),
                stop_reason, 1 if tool_calls_list else 0
            ))

            for tc in tool_calls_list:
                tc_result = tool_call_results.get(tc["id"], "")
                c.execute("""
                    INSERT OR REPLACE INTO tool_calls
                    (id, message_id, tool_name, arguments, result)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    tc["id"], event_id, tc["name"],
                    json.dumps(tc["arguments"], ensure_ascii=False),
                    tc_result
                ))
