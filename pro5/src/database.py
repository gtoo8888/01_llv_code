"""
数据库操作
"""
import sqlite3
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

    conn.commit()
    conn.close()
