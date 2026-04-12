# pro5 功能路线图（未来版）

> 本文档记录已规划但暂不实现的功能，供后续迭代参考。

---

## Phase 2：统计分析

### 仪表盘（index.html 增强）

在现有会话列表页基础上，增加统计概览：

**统计卡片**：
- 总消息数
- 总会话数
- 总 Token 消耗
- 数据日期范围

**图表**：
- 每日消息趋势折线图（Canvas 绘制）
- 渠道/模型分布饼图

**API 扩展**：
- `GET /api/stats` — 全局统计摘要
- `GET /api/stats/daily` — 每日趋势数据
- `GET /api/stats/distribution` — 分布数据

---

## Phase 3：交互增强

### 筛选与搜索
- 按渠道筛选（feishu / telegram / webchat）
- 按日期范围筛选
- 关键词搜索对话内容

**API 扩展**：
- `GET /api/sessions?channel=feishu&date_from=2026-03-01`
- `GET /api/search?q=多Agent`

### 分页
- 会话列表分页（每页20条）
- 消息详情分页（每页50条）

---

## Phase 4：数据管理

### 增量解析
- 扫描 `03_workspace/03_drafts/` 目录
- 检测新 JSONL 文件
- 只解析未入库的文件
- 记录解析进度

**脚本扩展**：
- `scripts/scan_source_dir.py` — 扫描源目录
- `scripts/incremental_parse.py` — 增量入库

### 原始数据管理
- 支持指定多个 JSONL 源目录
- 原始文件复制到 `data/raw/` 归档

---

## Phase 5：导出与分享

### Markdown 导出
- `GET /api/sessions/{key}/export/markdown` — 单会话导出
- 前端增加"导出"按钮

### JSON 导出
- 导出完整或筛选后的数据

---

## Phase 6：高级功能

### 多数据源接入
- 支持其他对话平台数据格式
- 适配层设计

### 会话对比
- 选中多个会话横向对比

### 收藏与标注
- 标记重要会话
- 添加备注

---

## 功能优先级汇总

| 优先级 | 功能 | 所属 Phase |
|--------|------|-----------|
| P1 | 仪表盘统计卡片 | Phase 2 |
| P1 | 每日趋势图 | Phase 2 |
| P1 | 渠道/模型分布图 | Phase 2 |
| P2 | 渠道筛选 | Phase 3 |
| P2 | 日期范围筛选 | Phase 3 |
| P2 | 会话列表分页 | Phase 3 |
| P3 | 关键词搜索 | Phase 3 |
| P3 | 增量解析 | Phase 4 |
| P3 | Markdown 导出 | Phase 5 |
| P4 | JSON 导出 | Phase 5 |
| P4 | 多数据源接入 | Phase 6 |
| P5 | 会话对比 | Phase 6 |
| P5 | 收藏标注 | Phase 6 |

---

_文档版本：v0.1_
_创建日期：2026-04-04_
