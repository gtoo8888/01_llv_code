# {Project Name}

{One-line description of what this project does.}

## 功能特性

- {Feature 1}
- {Feature 2}
- {Feature 3}

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python FastAPI |
| 数据库 | SQLite |
| 前端 | 原生 HTML + CSS + JavaScript（无框架）|
| 环境 | Conda |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
./auto_run.sh run
```

### 3. 访问

- 本地：http://localhost:{port}
- 局域网：http://{IP}:{port}

## 页面说明

| 页面 | 地址 | 说明 |
|------|------|------|
| 首页 | / | 主页面/导航页 |
| {页面1} | /{page-1}.html | {说明} |
| {页面2} | /{page-2}.html | {说明} |

## 目录结构

```
.
├── app.py                  # FastAPI 后端入口
├── requirements.txt        # Python 依赖
├── database.db             # SQLite 数据库（自动生成）
├── auto_run.sh            # 服务管理脚本
├── README.md              # 项目说明（本文档）
├── doc/
│   ├── DEVELOPMENT.md      # 开发指南
│   └── todo.md            # 开发计划/任务清单
├── test/
│   ├── test_main.py       # 测试示例
│   └── test_xxx.py        # 按模块组织测试
└── static/                # 静态资源
    ├── index.html         # 主页面/导航页
    ├── {page-1}.html      # 功能页1
    ├── {page-2}.html      # 功能页2
    ├── css/
    │   ├── style.css      # 公共样式
    │   ├── {page-1}.css   # 页面1专属样式
    │   └── {page-2}.css   # 页面2专属样式
    └── js/
        ├── api.js         # API 调用封装
        ├── utils.js       # 工具函数
        ├── {page-1}.js    # 页面1业务逻辑
        └── {page-2}.js    # 页面2业务逻辑
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /api/data` | GET | 获取数据 |
| `POST /api/action` | POST | 执行操作 |

## 服务管理

```bash
./auto_run.sh run      # 启动
./auto_run.sh stop     # 停止
./auto_run.sh status   # 状态
./auto_run.sh logs     # 日志
./auto_run.sh restart  # 重启
```

## 测试

```bash
python -m pytest -v
```

## 开发指南

详见 [doc/DEVELOPMENT.md](./doc/DEVELOPMENT.md)
