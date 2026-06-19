#!/usr/bin/env python3
"""
对话数据分析平台 - FastAPI 后端入口
"""
import json
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.config import STATIC_DIR, BASE_DIR
from src.database import init_db, get_conn, ensure_all_sessions_init
from src.parser import scan_and_parse
from src.routes import router


app = FastAPI(title="pro5 对话数据分析平台")

# 挂载路由
app.include_router(router)

# 静态文件
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def startup():
    """启动时初始化数据库 + 增量解析新文件 + 预填 DeepSeek 对话 ID 到状态表"""
    init_db()
    scan_and_parse()

    # 预填所有 DeepSeek 对话 ID 到 conversation_status 表
    deepseek_archive = BASE_DIR / "llm_conversation_archives" / "deepseek_data-merged"
    if deepseek_archive.exists():
        all_ids = []
        for year_dir in sorted(deepseek_archive.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir():
                    continue
                data_file = month_dir / "_data.json"
                if not data_file.exists():
                    continue
                try:
                    with open(data_file, "r", encoding="utf-8") as f:
                        sessions = json.load(f)
                    for s in sessions:
                        sid = s.get("id", "")
                        if sid:
                            all_ids.append(sid)
                except (json.JSONDecodeError, IOError):
                    continue

        if all_ids:
            conn = get_conn()
            ensure_all_sessions_init(conn, all_ids)
            conn.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
