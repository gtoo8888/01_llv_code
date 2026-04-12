#!/usr/bin/env python3
"""
Step 1: JSONL Parser
Parse OpenClaw session JSONL files, build readable conversation structure
"""
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# ============ Config ============
DB_PATH = "/data_sdb/openclaw/KnowledgeWorkspace/02_llv_generated/01_llv_code/pro5/database.db"
JSON_OUTPUT = "/data_sdb/openclaw/KnowledgeWorkspace/02_llv_generated/01_llv_code/pro5/data/parsed/all_conversations.json"
MD_OUTPUT = "/data_sdb/openclaw/KnowledgeWorkspace/02_llv_generated/01_llv_code/pro5/data/parsed/all_conversations.md"
SOURCE_FILE = "/data_sdb/openclaw/KnowledgeWorkspace/03_workspace/03_drafts/0d23113d-9faa-48b8-b61d-cd3e546189f4.jsonl.reset.2026-04-03T12-04-56.005Z"
LIMIT = None  # None = parse all


# ============ Database Initialization ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_key TEXT PRIMARY KEY,
            start_time TEXT,
            cwd TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_key TEXT NOT NULL,
            parent_id TEXT,
            role TEXT,
            content TEXT,
            raw_content TEXT,
            thinking TEXT,
            timestamp TEXT,
            model TEXT,
            provider TEXT,
            channel TEXT,
            tokens_input INTEGER DEFAULT 0,
            tokens_output INTEGER DEFAULT 0,
            tokens_total INTEGER DEFAULT 0,
            stop_reason TEXT,
            FOREIGN KEY (session_key) REFERENCES sessions(session_key)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tool_calls (
            id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            tool_name TEXT,
            arguments TEXT,
            result TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id)
        )
    """)

    conn.commit()
    conn.close()


# ============ Parsing Utilities ============
def extract_content_detail(content_list):
    """
    Extract various content types from message content array
    Returns: (readable_text, thinking_text, tool_calls_list)
    """
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

        elif item_type == "toolResult":
            # toolResult is usually an independent message, paired with its toolCall via parentId
            pass

    return "\n".join(readable_parts), "\n".join(thinking_parts), tool_calls


def parse_jsonl(source_file: str, limit: Optional[int] = None):
    """
    Parse JSONL line by line, build conversation tree
    Returns: (sessions_dict, messages_list)
    """
    sessions = {}  # session_key -> session info
    messages = []  # messages in chronological order
    tool_call_results = {}  # message_id -> toolResult content (for pairing)

    path = Path(source_file)
    if not path.exists():
        print(f"[ERROR] File not found: {source_file}")
        sys.exit(1)

    current_session_key = None

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            if limit and line_num >= limit:
                break

            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[WARN] Line {line_num+1} JSON parse failed: {e}")
                continue

            event_type = event.get("type", "")
            event_id = event.get("id", "")
            parent_id = event.get("parentId")
            timestamp = event.get("timestamp", "")

            # ---- session ----
            if event_type == "session":
                current_session_key = event.get("id", "")
                sessions[current_session_key] = {
                    "session_key": current_session_key,
                    "start_time": timestamp,
                    "cwd": event.get("cwd", ""),
                }
                continue

            # Only "message" type events go into messages table
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

            # Extract various content types
            readable_text, thinking_text, tool_calls_list = extract_content_detail(content_list)

            # toolResult may appear as an independent message
            # content_list normally doesn't contain toolResult, but handle it defensively
            if role == "tool":
                # tool role messages may have toolResult format in content array
                readable_text = ""
                for item in content_list:
                    if isinstance(item, dict):
                        if item.get("type") == "toolResult":
                            result_content = item.get("content", "")
                            if isinstance(result_content, list):
                                for r in result_content:
                                    if isinstance(r, dict) and r.get("type") == "text":
                                        readable_text = r.get("text", "")
                            elif isinstance(result_content, str):
                                readable_text = result_content
                            tool_call_results[parent_id] = readable_text

            message_record = {
                "id": event_id,
                "session_key": current_session_key or "unknown",
                "parent_id": parent_id,
                "role": role,
                "content": readable_text,
                "raw_content": json.dumps(content_list, ensure_ascii=False),
                "thinking": thinking_text,
                "timestamp": timestamp,
                "model": model,
                "provider": provider,
                "channel": api or provider,  # use api or provider as channel identifier
                "tokens_input": usage.get("input", 0),
                "tokens_output": usage.get("output", 0),
                "tokens_total": usage.get("totalTokens", 0),
                "stop_reason": stop_reason,
                "tool_calls": tool_calls_list,  # temporarily stored, will be written to DB later
            }

            messages.append(message_record)

    # Pair tool calls with their results
    for msg in messages:
        tool_calls_with_results = []
        for tc in msg.get("tool_calls", []):
            tc["result"] = tool_call_results.get(tc["id"], "")
            tool_calls_with_results.append(tc)
        msg["tool_calls"] = tool_calls_with_results

    return sessions, messages


def save_to_db(sessions: dict, messages: list):
    """Write to SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Write sessions
    for s in sessions.values():
        c.execute("""
            INSERT OR REPLACE INTO sessions (session_key, start_time, cwd)
            VALUES (?, ?, ?)
        """, (s["session_key"], s["start_time"], s["cwd"]))

    # Write messages
    for m in messages:
        c.execute("""
            INSERT OR REPLACE INTO messages
            (id, session_key, parent_id, role, content, raw_content, thinking,
             timestamp, model, provider, channel, tokens_input, tokens_output,
             tokens_total, stop_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m["id"], m["session_key"], m["parent_id"], m["role"],
            m["content"], m["raw_content"], m["thinking"],
            m["timestamp"], m["model"], m["provider"], m["channel"],
            m["tokens_input"], m["tokens_output"], m["tokens_total"],
            m["stop_reason"]
        ))

        # 写入 tool_calls
        for tc in m.get("tool_calls", []):
            c.execute("""
                INSERT OR REPLACE INTO tool_calls
                (id, message_id, tool_name, arguments, result)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tc["id"], m["id"], tc["name"],
                json.dumps(tc["arguments"], ensure_ascii=False),
                str(tc.get("result", ""))[:5000]  # 截断超长结果
            ))

    conn.commit()
    conn.close()


def save_to_json(sessions: dict, messages: list):
    """Export full data as JSON (complete, no data loss)"""
    Path(JSON_OUTPUT).parent.mkdir(parents=True, exist_ok=True)

    # Group by session_key
    by_session = {}
    for m in messages:
        sk = m["session_key"]
        if sk not in by_session:
            by_session[sk] = {
                "session_key": sk,
                "start_time": sessions.get(sk, {}).get("start_time", ""),
                "cwd": sessions.get(sk, {}).get("cwd", ""),
                "messages": []
            }
        by_session[sk]["messages"].append(m)

    output = {
        "generated_at": datetime.now().isoformat(),
        "source_file": SOURCE_FILE,
        "total_sessions": len(sessions),
        "total_messages": len(messages),
        "sessions": list(by_session.values())
    }

    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[OK] JSON exported: {JSON_OUTPUT}")


def save_to_markdown(sessions: dict, messages: list):
    """Export human-readable Markdown format"""
    Path(MD_OUTPUT).parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Conversation Records\n",
        f"> Source: `{SOURCE_FILE}`\n",
        f"> Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"> Total sessions: {len(sessions)} | Total messages: {len(messages)}\n",
        "---\n"
    ]

    # Group by session
    by_session = {}
    for m in messages:
        sk = m["session_key"]
        if sk not in by_session:
            by_session[sk] = []
        by_session[sk].append(m)

    for sk, session_msgs in by_session.items():
        session_info = sessions.get(sk, {})
        start = session_info.get("start_time", "Unknown")
        cwd = session_info.get("cwd", "")

        lines.append(f"## Session {sk[:16]}...\n")
        lines.append(f"- **Start Time:** {start}")
        lines.append(f"- **Working Dir:** `{cwd}`\n")

        for m in session_msgs:
            ts = m["timestamp"]
            role = m["role"]
            role_display = {
                "user": "**User**",
                "assistant": "**Assistant**",
                "system": "**System**",
                "tool": "**Tool**"
            }.get(role, f"**{role}**")

            model = m["model"] or m["provider"] or "-"
            tokens = m["tokens_total"]
            stop = m["stop_reason"] or "-"

            lines.append(f"### {role_display} | {ts} | {model}\n")
            lines.append(f"> Timestamp: `{ts}` | Tokens: {tokens} | Stop: `{stop}`\n")

            # Tool calls
            if m.get("tool_calls"):
                lines.append("**Tool Calls:**\n")
                for tc in m["tool_calls"]:
                    args = tc.get("arguments", {})
                    args_str = json.dumps(args, ensure_ascii=False)
                    lines.append(f"```json\n// {tc['name']}\n{args_str}\n```\n")
                    if tc.get("result"):
                        result_text = tc["result"][:1000] + ("..." if len(tc["result"]) > 1000 else "")
                        lines.append(f"**Result:**\n```\n{result_text}\n```\n")

            # Thinking
            if m.get("thinking"):
                lines.append("**Thinking:**\n```\n")
                thinking = m["thinking"]
                if len(thinking) > 3000:
                    thinking = thinking[:3000] + "\n...(truncated)"
                lines.append(thinking + "\n```\n")

            # Message content
            if m.get("content"):
                lines.append(f"{m['content']}\n")

            lines.append("---\n")

    with open(MD_OUTPUT, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"[OK] Markdown exported: {MD_OUTPUT}")


def print_preview(sessions: dict, messages: list, count: int = 10):
    """Print parsing preview to stdout"""
    print(f"\n{'='*70}")
    print(f"[OK] Parsing complete")
    print(f"   Sessions: {len(sessions)}")
    print(f"   Messages: {len(messages)}")
    print(f"{'='*70}\n")

    print(f"--- Sessions ---")
    for sk, s in list(sessions.items())[:5]:
        print(f"  {sk[:16]}...  started: {s['start_time']}")

    print(f"\n--- Last {count} messages preview ---")
    for m in messages[-count:]:
        role = m["role"].upper()
        content_preview = m["content"][:80].replace("\n", " ") if m["content"] else "[no text]"
        if len(m["content"]) > 80:
            content_preview += "..."
        thinking_note = " [has thinking]" if m["thinking"] else ""
        tool_note = f" [tool calls x{len(m['tool_calls'])}]" if m["tool_calls"] else ""
        print(f"  [{role}] {content_preview}{thinking_note}{tool_note}")


# ============ Main Entry ============
if __name__ == "__main__":
    print(f"Source: {SOURCE_FILE}")
    print(f"Database: {DB_PATH}")
    print(f"Environment: llm_chat_dashboard")

    init_db()
    print("[OK] Database initialized")

    sessions, messages = parse_jsonl(SOURCE_FILE, limit=LIMIT)
    print_preview(sessions, messages)

    save_to_db(sessions, messages)
    print(f"[OK] Data written to database: {DB_PATH}")

    save_to_json(sessions, messages)
    save_to_markdown(sessions, messages)
