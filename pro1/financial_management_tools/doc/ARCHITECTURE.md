# 技术架构说明

## 当前架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Browser)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ welcome.html │  │ calculator  │  │  indices    │        │
│  │             │  │   .html     │  │   .html     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         ↓                  ↓                  ↓              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  JavaScript (app.js / calculator.js / indices.js)    │   │
│  │  - 发起 API 请求                                      │   │
│  │  - 处理用户交互                                        │   │
│  │  - 渲染页面数据                                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓ HTTP 请求
┌─────────────────────────────────────────────────────────────┐
│                      后端 (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  app/                                               │   │
│  │  ├── routers/          # 路由模块                    │   │
│  │  │   ├── wealth.py     # 理财计算                   │   │
│  │  │   ├── indices.py    # 指数行情                   │   │
│  │  │   └── chart.py     # 图表                      │   │
│  │  ├── services/        # 业务逻辑                    │   │
│  │  │   ├── calculator.py                           │   │
│  │  │   └── akshare_helper.py  # 数据获取            │   │
│  │  ├── models.py       # SQLAlchemy 模型            │   │
│  │  ├── schemas.py      # Pydantic 模型              │   │
│  │  └── database.py    # 数据库连接                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                 │
│                    SQLite 数据库                            │
└─────────────────────────────────────────────────────────────┘
```

## 前后端职责

### 前端 (static/)

| 文件 | 职责 |
|------|------|
| `welcome.html` | 首页 |
| `wealth.html` | 理财收益计算器 |
| `calculator.html` | 收益率计算器 |
| `chart.html` | 收益走势图表 |
| `indices.html` | 指数行情 |
| `css/style.css` | 全局样式 |
| `css/indices.css` | 指数行情样式 |
| `js/app.js` | 理财计算器交互逻辑 |
| `js/calculator.js` | 收益率计算器交互逻辑 |
| `js/indices.js` | 指数行情交互逻辑 |

**前端任务：**
- 页面渲染和展示
- 用户输入验证
- 发起 HTTP 请求到后端
- 处理响应数据，更新 DOM
- 交互效果和动画

### 后端 (app/)

| 路由 | 职责 |
|------|------|
| `GET /` | 返回 welcome.html |
| `GET /wealth.html` | 返回 wealth.html |
| `GET /indices.html` | 返回 indices.html |
| `GET /calculator.html` | 返回 calculator.html |
| `GET /chart.html` | 返回 chart.html |
| `GET /static/*` | 返回静态资源 |
| `POST /calculate` | 计算收益，保存到数据库 |
| `GET /records` | 获取历史记录 |
| `GET /api/indices` | 获取指数行情（抓取数据） |
| `GET /api/indices/progress` | 获取抓取进度 |
| `GET /api/indices/cached` | 获取缓存的指数数据 |

**后端任务：**
- 提供 HTML 页面
- 处理业务逻辑（收益率计算、行情数据抓取）
- 数据持久化（SQLite）
- 提供 REST API 接口

## 前后端分离的优势

| 优势 | 说明 |
|------|------|
| 🎯 **职责清晰** | 前端负责展示，后端负责数据 |
| 🔄 **独立开发** | 前后端可以并行开发 |
| 🔌 **松耦合** | 通过 API 通信，互不影响 |
| 📱 **多端复用** | 同一套 API 支持 Web、iOS、Android |
| 🧪 **易于测试** | API 可以独立测试 |

## 模块化架构

项目采用模块化架构，将代码拆分到 `app/` 目录：

```
app/
├── __init__.py       # 包初始化
├── config.py         # 配置
├── database.py       # 数据库连接
├── models.py         # SQLAlchemy 模型（Record, IndexQuote）
├── schemas.py        # Pydantic 模型（请求/响应）
├── routers/          # 路由模块
│   ├── wealth.py    # 理财计算相关路由
│   ├── indices.py   # 指数行情相关路由
│   └── chart.py     # 图表相关路由
└── services/         # 业务逻辑
    ├── calculator.py # 收益计算逻辑
    └── akshare_helper.py  # 数据抓取工具
```

## 为什么不完全分离？

当前设计是「半分离」：

| 方面 | 当前方案 | 完全分离方案 |
|------|----------|--------------|
| 前端构建 | 原生 HTML + JS | Vite + React/Vue |
| 后端 | FastAPI + 页面渲染 | 仅提供 API |
| 静态文件 | FastAPI StaticFiles | Nginx / CDN |

**当前方案适合：**
- ✅ 小型项目
- ✅ 快速开发
- ✅ 个人使用

**完全分离适合：**
- ✅ 团队协作
- ✅ 大型项目
- ✅ 需要 SEO

## 扩展说明

如果未来需要完全分离，可以这样改造：

```
前端项目 (独立仓库)
├── vite.config.js
├── src/
│   ├── App.vue
│   └── ...
└── package.json
        ↓ npm run build
        ↓ 静态文件部署到 Nginx
              ↓
后端 API (FastAPI)
└── 仅提供 /api/* 接口
```
