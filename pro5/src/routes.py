"""
API 路由
"""
import json
from fastapi import APIRouter

from src.config import DB_PATH, STATIC_DIR
from src.database import get_conn
from src.parser import strip_user_metadata

router = APIRouter()


@router.get("/api/sessions")
def get_sessions():
    """会话列表"""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT
            m.session_key,
            MIN(m.timestamp) as start_time,
            COUNT(m.id) as message_count,
            MAX(m.channel) as channel
        FROM messages m
        GROUP BY m.session_key
        ORDER BY start_time DESC
    """)

    rows = c.fetchall()
    conn.close()

    return {
        "sessions": [
            {
                "session_key": row[0],
                "start_time": row[1],
                "message_count": row[2],
                "channel": row[3] or "unknown",
            }
            for row in rows
        ]
    }


@router.get("/api/sessions/{session_key}/messages")
def get_session_messages(session_key: str):
    """某会话的所有消息"""
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT channel FROM sessions WHERE session_key = ?", (session_key,))
    row = c.fetchone()
    channel = row[0] if row else "unknown"

    c.execute("""
        SELECT id, role, content, thinking, timestamp, model,
               parent_id, has_tool_calls
        FROM messages
        WHERE session_key = ?
        ORDER BY timestamp ASC
    """, (session_key,))

    rows = c.fetchall()

    c.execute("""
        SELECT id, message_id, tool_name, arguments, result
        FROM tool_calls
        WHERE message_id IN (SELECT id FROM messages WHERE session_key = ?)
    """, (session_key,))
    tc_rows = c.fetchall()

    tool_calls_map = {}
    for tc_row in tc_rows:
        msg_id = tc_row[1]
        if msg_id not in tool_calls_map:
            tool_calls_map[msg_id] = []
        tool_calls_map[msg_id].append({
            "id": tc_row[0],
            "name": tc_row[2],
            "arguments": json.loads(tc_row[3]) if tc_row[3] else {},
            "result": tc_row[4],
        })

    conn.close()

    messages = []
    for row in rows:
        msg_id, role, content, thinking, timestamp, model, parent_id, has_tc = row
        is_system = bool(content and content.startswith("System:"))

        msg = {
            "id": msg_id,
            "role": role,
            "content": strip_user_metadata(content) if role == "user" else (content or ""),
            "timestamp": timestamp,
            "model": model or "",
            "is_system": is_system,
            "parent_id": parent_id,
        }

        if has_tc and msg_id in tool_calls_map:
            msg["tool_calls"] = tool_calls_map[msg_id]

        messages.append(msg)

    return {
        "session_key": session_key,
        "channel": channel,
        "messages": messages,
    }


@router.get("/")
def serve_index():
    """首页 -> 会话列表"""
    from fastapi.responses import FileResponse
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/sessions")
def serve_sessions_page():
    """会话列表页（别名）"""
    from fastapi.responses import FileResponse
    return FileResponse(STATIC_DIR / "index.html")
