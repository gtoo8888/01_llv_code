# 论文库可视化

目录树浏览器，支持指定任意目录并以多种形式可视化展示论文分布。

## 环境

```bash
conda env: paper_dashboard
Python: 3.10.20
fastapi: 0.135.1
uvicorn: 0.42.0
```

## 快速开始

### 激活环境

```bash
source ~/anaconda3/etc/profile.d/conda.sh
conda activate paper_dashboard
```

### 启动服务

```bash
cd /data_sdb/openclaw/02_llv_generated/01_llv_code/pro2
python app.py
```

或使用管理脚本：

```bash
./auto_run.sh run      # 启动
./auto_run.sh stop     # 停止
./auto_run.sh restart  # 重启
./auto_run.sh status   # 状态
./auto_run.sh logs     # 查看日志
```

### 访问

- **概览页**：http://localhost:8001/
- **目录树页**：http://localhost:8001/tree.html
- **旭日图页**：http://localhost:8001/sunburst.html
- **词云页**：http://localhost:8001/wordcloud.html
- 局域网：把 localhost 换成机器 IP

## 功能特性

### 页面结构

单一页面内嵌多个标签页，通过顶部标签栏切换：

| 标签     | 功能                        |
| -------- | --------------------------- |
| 📊 概览   | 输入路径 → 显示学科分布表格 |
| 🌲 目录树 | 可折叠的树状目录结构        |
| ☀️ 旭日图 | 独立页面，支持点击下钻      |
| ☁️ 词云   | 独立页面，学科词云          |

### 📊 概览

- 输入目录路径，点击「加载」
- 顶部卡片展示：目录数、文件总数、一级学科数
- **学科分布表格**：
  - 按层级显示一级 / 二级 / 三级学科
  - 每行显示学科名称 + 论文数量
  - 点击一级学科行展开/折叠其所有子类
  - 点击二级学科行展开/折叠其所有子类
  - 学科名称自动格式化（`02_Economics` → `Economics`）
  - PDF 数量统计不受「显示文件」开关影响，始终准确

> 📎 参考链接：[学位学科和研究生教育发展简报](https://www.cdgdc.edu.cn/dslxkpgjggb/index.htm)

### 🌲 目录树

- 输入目录路径，点击「加载」
- 可折叠的树状结构，支持展开/折叠任意文件夹
- 文件夹显示子目录和文件数量
- 文件/文件夹图标区分
- 路径自动保存到 sessionStorage，刷新后无需重新输入

## 接口

### POST /tree

扫描指定目录返回树结构。

**请求体：**
```json
{
  "path": "/data_sdb/openclaw/01_data/04_papers/raw",
  "include_files": false
}
```

**响应：**
```json
[
  {
    "name": "02_Economics",
    "children": [
      {
        "name": "0202_Applied_Economics",
        "children": [],
        "paper_count": 18
      }
    ],
    "paper_count": 18
  }
]
```

## 技术栈

- **后端**：Python FastAPI
- **前端**：原生 HTML + CSS + JavaScript（无框架）
- **样式**：HTML/CSS 树形结构和表格

## 文件结构

```
pro2/
├── app.py                  # FastAPI 主程序
├── auto_run.sh            # 服务管理脚本
├── README.md              # 项目说明
├── PROJECT_PLAN.md        # 开发计划
└── static/
    ├── overview.html       # 概览页
    ├── tree.html           # 目录树页
    ├── sunburst.html       # 旭日图页
    ├── wordcloud.html      # 词云页
    ├── css/
    │   ├── style.css      # 公共样式
    │   ├── overview.css   # 概览页样式
    │   ├── tree.css       # 目录树样式
    │   ├── sunburst.css   # 旭日图样式
    │   └── wordcloud.css  # 词云样式
    └── js/
        ├── api.js         # API 调用
        ├── overview.js    # 概览页逻辑
        ├── tree.js        # 目录树逻辑
        ├── sunburst.js    # 旭日图逻辑
        └── wordcloud.js   # 词云逻辑
```

## 未来演进

- ~~☀️ 旭日图（sunburst）按层级展示分布占比~~ ✅ 已实现
- ~~☁️ 词云 — 高频词可视化~~ ✅ 已实现（学科词云）
- 搜索功能
- PDF 全文内容提取
- 作者合作网络图
- PDF 在线预览
