# 开发指南

本文档供大模型阅读，帮助快速了解项目结构、开发规范和注意事项。

---

## 项目概述

- **项目名称**: 理财收益计算器
- **功能**: 理财产品收益计算、A股指数行情、收益走势可视化
- **技术栈**: Python + FastAPI + SQLite + 原生 HTML/CSS/JS + ECharts + Akshare

---

## ⚠️ 开发原则（大模型必须遵守）

### 1. 前后端联动实现

- **不要只写前端或只写后端**，实现一个功能需要前后端配合
- 新增页面时，除了创建 HTML/CSS/JS，还需要添加对应的后端路由
- 如果需要数据交互，必须同时提供 API 接口

### 2. 开发前先确认需求

- **不要马上开始编码**，先和用户确认具体细节
- 确认内容包括：数据来源、展示形式、筛选条件、交互方式等
- 必要时可以先列出方案供用户选择

### 3. 后端代码需添加单元测试

- 完成后询问用户是否需要添加单元测试
- 如果需要，在 `test_main.py` 中添加测试用例
- 运行测试: `python3 -m pytest test_main.py -v`

### 4. 前端代码做好拆分

- 一个功能对应一个 HTML 文件
- CSS 和 JS 必须拆分到独立文件，禁止大量内联代码
- 页面导航必须包含，方便页面跳转

---

## 项目结构

```
/date_sdb/soft/openclaw/code/
├── main.py                    # FastAPI 入口（汇总路由）
├── app/                       # 应用代码（模块化）
│   ├── __init__.py
│   ├── config.py              # 配置
│   ├── database.py            # 数据库连接
│   ├── models.py              # SQLAlchemy 模型
│   ├── schemas.py             # Pydantic 模型
│   ├── routers/               # 路由模块
│   │   ├── wealth.py          # 理财计算路由
│   │   ├── indices.py         # 指数行情路由
│   │   └── chart.py          # 图表路由
│   └── services/              # 业务逻辑
│       ├── calculator.py       # 收益计算
│       └── akshare_helper.py  # 数据抓取
├── database.db                # SQLite 数据库
├── auto_run.sh               # 服务启动/停止脚本
├── requirements.txt           # Python 依赖
├── test_main.py              # 单元测试
├── test_akshare.py           # Akshare 测试
├── README.md                 # 项目说明
├── doc/                      # 技术文档
└── static/                   # 静态资源
    ├── welcome.html           # 首页
    ├── wealth.html           # 理财收益计算器
    ├── calculator.html       # 收益率计算器
    ├── chart.html           # 收益走势图表
    ├── indices.html         # 指数行情
    ├── css/
    │   ├── style.css
    │   ├── calculator.css
    │   ├── chart.css
    │   ├── welcome.css
    │   └── indices.css
    └── js/
        ├── app.js
        ├── calculator.js
        ├── chart.js
        └── indices.js
```

---

## 启动与停止

```bash
cd /date_sdb/soft/openclaw/code

# 启动服务
./auto_run.sh run

# 停止服务
./auto_run.sh stop

# 重启服务
./auto_run.sh restart

# 查看日志
./auto_run.sh logs
```

访问地址: **http://localhost:8081**

---

## 前端开发规范

### 1. 页面文件命名

- 使用英文命名，如 `welcome.html`、`wealth.html`、`indices.html`
- 避免使用 `index.html` 作为业务页面（保留给首页）

### 2. HTML 结构

每个页面应包含：
- 正确的 meta 标签
- 引入 `style.css` 和页面专用 CSS
- 页面导航（所有页面必须包含，方便跳转）

```html
<!-- 页面导航示例 -->
<div class="page-nav">
    <a href="/" class="nav-link">🏠 首页</a>
    <a href="/wealth.html" class="nav-link">📊 理财收益计算器</a>
    <a href="/indices.html" class="nav-link">📈 指数行情</a>
</div>
```

### 3. CSS 拆分规则

- **全局样式** → `css/style.css`
- **页面专用样式** → `css/<页面名>.css`
- **禁止在 HTML 中使用大量内联 `<style>`**

引入方式：
```html
<link rel="stylesheet" href="/static/css/style.css">
<link rel="stylesheet" href="/static/css/xxx.css">
```

### 4. JavaScript 拆分规则

- **业务逻辑** → `js/<页面名>.js`
- **禁止在 HTML 中直接写大量 JS**

引入方式（放在 `</body>` 前）：
```html
<script src="/static/js/xxx.js"></script>
```

### 5. ECharts / Flatpickr 使用

- ECharts: `https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js`
- Flatpickr: `https://cdn.jsdelivr.net/npm/flatpickr@4.6.13/dist/flatpickr.min.js`

---

## 后端开发规范

### 1. 模块化结构

新增功能时，根据功能类型选择对应的路由文件：

| 功能类型 | 路由文件 | 适用场景 |
|----------|----------|----------|
| 理财相关 | `app/routers/wealth.py` | 收益计算、记录管理 |
| 指数行情 | `app/routers/indices.py` | 行情数据、进度查询 |
| 图表数据 | `app/routers/chart.py` | 走势图表 |

### 2. 添加新页面路由

在对应的路由文件中添加：

```python
# app/routers/xxx.py
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
import os

router = APIRouter()
STATIC_DIR = "static"

def read_html(filename: str) -> str:
    path = os.path.join(STATIC_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Page not found</h1>"

@router.get("/xxx.html", response_class=HTMLResponse)
async def read_xxx():
    """返回xxx页面"""
    return read_html("xxx.html")
```

### 3. 添加 API 接口

在对应的路由文件中添加：

```python
# 请求模型定义在 app/schemas.py
from app.schemas import XxxRequest, XxxResponse

@router.post("/api/xxx", response_model=XxxResponse)
async def xxx_endpoint(data: XxxRequest):
    # 业务逻辑
    return {"result": value}
```

### 4. 数据库操作

使用 `app/database.py` 中的 SessionLocal：

```python
from app.database import SessionLocal
from app.models import Record, IndexQuote

db = SessionLocal()
try:
    # CRUD 操作
    record = db.query(Record).filter(Record.id == record_id).first()
finally:
    db.close()
```

模型定义在 `app/models.py`：
- `Record` - 理财记录
- `IndexQuote` - 指数行情

### 5. 注册路由

路由文件创建后，需要在 `main.py` 中注册：

```python
# main.py
from app.routers import wealth, indices, chart

app.include_router(wealth.router, tags=["wealth"])
app.include_router(indices.router, tags=["indices"])
app.include_router(chart.router, tags=["chart"])
```

### 6. 服务重启

修改后端代码需要重启服务：

```bash
./auto_run.sh restart
```

### 7. 单元测试

```bash
python3 -m pytest test_main.py -v
```

---

## 添加新页面的完整流程

假设要添加一个新页面 `analysis.html`：

### 1. 创建前端文件

- `static/analysis.html` - HTML 结构
- `static/css/analysis.css` - 样式
- `static/js/analysis.js` - 交互逻辑

### 2. 添加后端路由

在 `app/routers/` 下创建或修改路由文件

### 3. 注册路由

在 `main.py` 中添加 `app.include_router()`

### 4. 更新导航

在所有页面的导航中添加链接

### 5. 重启服务

```bash
./auto_run.sh restart
```

---

## 注意事项

### ⚠️ 核心原则

> **实现任何功能时，必须同时考虑前端和后端，确保前后端联动实现。**

### 1. 前后端数据交互

```javascript
const response = await fetch('/api/xxx');
const data = await response.json();
```

### 2. 防反爬策略

获取外部数据时需要间隔：

```python
import time
time.sleep(1)  # 每次请求间隔1秒
```

### 3. 服务端口

- 默认端口: **8081**

---

## 常见问题

### Q: 如何查看后端日志？
```bash
./auto_run.sh logs
```

### Q: 如何添加新的数据库字段？
1. 在 `app/models.py` 的模型类中添加新字段
2. SQLite 需要注意：新增列对已有数据默认为 NULL

### Q: 前端页面不显示？
1. 检查服务是否启动: `./auto_run.sh status`
2. 重启服务: `./auto_run.sh restart`
3. 查看日志排查错误

---

## 相关文档

- [README.md](../README.md) - 项目介绍与快速开始
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 技术架构
- [DEPLOY.md](./DEPLOY.md) - 部署指南
- [DEVELOP_ISSUES.md](./DEVELOP_ISSUES.md) - 开发问题记录
- [OPTIMIZATION.md](./OPTIMIZATION.md) - 性能优化记录
