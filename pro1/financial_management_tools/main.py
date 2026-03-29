from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from app.config import STATIC_DIR
from app.routers import wealth, indices, chart

# 创建 FastAPI 应用
app = FastAPI(title="理财收益计算器")

# 挂载静态文件目录
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 注册路由
app.include_router(wealth.router, tags=["wealth"])
app.include_router(indices.router, tags=["indices"])
app.include_router(chart.router, tags=["chart"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
