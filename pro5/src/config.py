"""
配置文件 — 路径常量
"""
from pathlib import Path

# 项目根目录（app.py 所在目录）
BASE_DIR = Path(__file__).parent.parent

DB_PATH = BASE_DIR / "database.db"

SOURCE_DIR = Path("/data_sdb/openclaw/KnowledgeWorkspace/02_llv_generated/01_llv_code/pro5/llm_sessions/openclaw")

STATIC_DIR = BASE_DIR / "static"
