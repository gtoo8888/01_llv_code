#!/usr/bin/env python3
"""
对话数据分析平台 - FastAPI 后端入口
"""
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.config import STATIC_DIR
from src.database import init_db
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
    """启动时初始化数据库 + 增量解析新文件"""
    init_db()
    scan_and_parse()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
