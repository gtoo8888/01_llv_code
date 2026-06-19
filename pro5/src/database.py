"""
数据库操作
"""
import sqlite3
from datetime import datetime
from src.config import DB_PATH


def get_conn():
    """获取数据库连接"""
    return sqlite3.connect(str(DB_PATH))


def init_db():
    """建表（如果不存在）"""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_key TEXT PRIMARY KEY,
            start_time TEXT,
            cwd TEXT,
            channel TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_key TEXT NOT NULL,
            parent_id TEXT,
            role TEXT,
            content TEXT,
            thinking TEXT,
            timestamp TEXT,
            model TEXT,
            provider TEXT,
            channel TEXT,
            tokens_input INTEGER DEFAULT 0,
            tokens_output INTEGER DEFAULT 0,
            tokens_total INTEGER DEFAULT 0,
            stop_reason TEXT,
            has_tool_calls INTEGER DEFAULT 0,
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

    # 记录已解析过的文件
    c.execute("""
        CREATE TABLE IF NOT EXISTS parsed_files (
            file_path TEXT PRIMARY KEY,
            parsed_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS conversation_status (
            id            TEXT PRIMARY KEY,
            status        TEXT NOT NULL DEFAULT 'raw',
            archived_at   TEXT,
            deleted_at    TEXT,
            notes         TEXT DEFAULT '',
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_status ON conversation_status(status)
    """)

    conn.commit()
    conn.close()


def get_or_init_status(conn, session_id):
    """
    懒初始化：查询对话状态，不存在则自动插入 status='raw'。
    返回 status dict 或 None（session_id 为空时）。
    """
    if not session_id:
        return None

    c = conn.cursor()
    c.execute("SELECT id, status, archived_at, deleted_at, notes, created_at, updated_at "
              "FROM conversation_status WHERE id = ?", (session_id,))
    row = c.fetchone()

    if row:
        return {
            "id": row[0],
            "status": row[1],
            "archived_at": row[2],
            "deleted_at": row[3],
            "notes": row[4],
        }

    # 懒初始化：自动插入 raw
    now = datetime.now().isoformat()
    c.execute(
        "INSERT INTO conversation_status (id, status, created_at, updated_at) VALUES (?, 'raw', ?, ?)",
        (session_id, now, now)
    )
    conn.commit()

    return {
        "id": session_id,
        "status": "raw",
        "archived_at": None,
        "deleted_at": None,
        "notes": "",
    }


def upsert_status(conn, session_id, status, notes=""):
    """更新对话状态，返回更新后的 status dict"""
    now = datetime.now().isoformat()
    c = conn.cursor()

    archived_at = now if status == "archived" else None
    deleted_at = now if status == "deleted" else None

    # 先确保记录存在（懒初始化）
    get_or_init_status(conn, session_id)

    c.execute(
        """UPDATE conversation_status
           SET status = ?, archived_at = COALESCE(?, archived_at),
               deleted_at = COALESCE(?, deleted_at),
               notes = COALESCE(?, notes),
               updated_at = ?
           WHERE id = ?""",
        (status, archived_at, deleted_at, notes, now, session_id)
    )
    conn.commit()

    return get_or_init_status(conn, session_id)


def get_status_for_sessions(conn, session_ids):
    """批量获取多个对话的状态，返回 { session_id: status_dict }"""
    if not session_ids:
        return {}

    c = conn.cursor()
    placeholders = ",".join("?" for _ in session_ids)
    c.execute(
        f"SELECT id, status, archived_at, deleted_at, notes FROM conversation_status "
        f"WHERE id IN ({placeholders})",
        session_ids
    )
    rows = c.fetchall()

    result = {}
    for row in rows:
        result[row[0]] = {
            "id": row[0],
            "status": row[1],
            "archived_at": row[2],
            "deleted_at": row[3],
            "notes": row[4],
        }

    return result


def get_status_counts(conn):
    """获取各状态的数量统计，返回 { total, raw, archived, deleted, deleted_permanent }"""
    c = conn.cursor()
    c.execute("SELECT status, COUNT(*) FROM conversation_status GROUP BY status")
    rows = c.fetchall()

    counts = {"raw": 0, "archived": 0, "deleted": 0, "deleted_permanent": 0}
    total = 0
    for status, count in rows:
        counts[status] = count
        total += count

    return {"total": total, **counts}


def permanent_delete_status(conn, session_id):
    """永久删除（仅标记为 deleted_permanent，不物理删除记录）"""
    now = datetime.now().isoformat()
    c = conn.cursor()
    c.execute(
        "UPDATE conversation_status SET status = 'deleted_permanent', updated_at = ? WHERE id = ?",
        (now, session_id)
    )
    conn.commit()


def ensure_all_sessions_init(conn, all_ids):
    """
    批量确保所有传入的 session ID 都已在 conversation_status 表中有记录。
    只插入不存在的 ID，状态为 'raw'。
    all_ids: list of session ID strings
    """
    if not all_ids:
        return

    c = conn.cursor()
    placeholders = ",".join("?" for _ in all_ids)
    c.execute(
        f"SELECT id FROM conversation_status WHERE id IN ({placeholders})",
        all_ids
    )
    existing = {row[0] for row in c.fetchall()}

    now = datetime.now().isoformat()
    new_ids = [sid for sid in all_ids if sid and sid not in existing]

    for sid in new_ids:
        c.execute(
            "INSERT INTO conversation_status (id, status, created_at, updated_at) VALUES (?, 'raw', ?, ?)",
            (sid, now, now)
        )

    if new_ids:
        conn.commit()
