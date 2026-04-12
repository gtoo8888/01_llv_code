# pro5 Web 界面设计文档（简化版）

> 核心目标：小步快跑，先把对话内容展示做好，其他都是未来的事。

---

## 一、当前目标

**只做一件事**：做一个人能看的对话展示页面。

---

## 二、项目结构

```
pro5/
├── app.py                      # FastAPI 后端（本次重点）
├── requirements.txt
├── database.db                 # 已有
├── auto_run.sh                 # 已有
├── scripts/
│   └── parse_conversations.py  # 已有
└── static/
    ├── index.html              # 会话列表页（极简）
    ├── conversation.html       # 对话详情页（核心）
    ├── css/
    │   └── style.css
    └── js/
        ├── api.js
        ├── index.js            # 会话列表逻辑
        └── conversation.js     # 对话详情逻辑
```

---

## 三、页面设计

### 3.1 index.html（会话列表）

只有一个功能：**选一个会话，点进去看详情**。

```
┌──────────────────────────────────────┐
│  对话历史                    [刷新]  │
├──────────────────────────────────────┤
│  ● 2026-03-10 13:04  feishu  23条   │
│  ● 2026-03-11 09:12  webchat  8条   │
│  ● 2026-03-12 14:30  feishu  15条   │
└──────────────────────────────────────┘
```

- 每一行 = 一个会话
- 点击行 → 跳转到 `conversation.html?id={session_key}`
- 暂时不做筛选、不做分页

### 3.2 conversation.html（对话详情）

核心页面，只做展示。

```
┌──────────────────────────────────────┐
│  ← 返回列表                          │
├──────────────────────────────────────┤
│  会话: 3561884e...  渠道: feishu     │
├──────────────────────────────────────┤
│                                      │
│  👤 User  ·  2026-03-10 13:04:06    │
│  System: [2026-03-10 21:03...]      │
│                                      │
│  ┌─ 🤖 Assistant · 13:04:06 ──────┐ │
│  │ 嘿呱呱！🐚                      │ │
│  │                                │ │
│  │  🔧 memory_search              │ │
│  │  {query: "..."}                │ │
│  │  ▼ 结果 (点击展开)              │ │
│  └────────────────────────────────┘ │
│                                      │
│  👤 User  ·  2026-03-10 13:05:00    │
│  开始新的任务...                     │
│                                      │
└──────────────────────────────────────┘
```

**展示规则**：
- User 消息：右对齐
- Assistant 消息：左对齐
- System 消息：居中、灰色小字
- Tool Call：内嵌在 Assistant 消息里，显示工具名 + 参数（可折叠）
- Tool Result：折叠，默认不显示
- Thinking：不显示（太冗长）

---

## 四、API 设计

只需要两个接口：

### 4.1 `GET /api/sessions`

返回会话列表，供 index.html 使用。

```json
{
  "sessions": [
    {
      "session_key": "3561884e-bd5d-4a8b-...",
      "start_time": "2026-03-10T13:04:06Z",
      "message_count": 23,
      "channel": "feishu"
    }
  ]
}
```

### 4.2 `GET /api/sessions/{session_key}/messages`

返回某会话的所有消息，供 conversation.html 使用。

```json
{
  "session_key": "3561884e-bd5d-4a8b-...",
  "channel": "feishu",
  "messages": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "System: [2026-03-10 21:03:50 GMT+8] ...",
      "timestamp": "2026-03-10T13:04:06Z",
      "is_system": true
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "嘿呱呱！🐚 看起来你今天...",
      "timestamp": "2026-03-10T13:04:11Z",
      "model": "MiniMax-M2.5",
      "tool_calls": [
        {
          "id": "tc_001",
          "name": "memory_search",
          "arguments": {"query": "recent sessions"},
          "result": "..."
        }
      ]
    },
    {
      "id": "msg_003",
      "role": "tool",
      "tool_call_id": "tc_001",
      "timestamp": "2026-03-10T13:04:11Z"
    }
  ]
}
```

**关键处理**：
- `role=tool` 的消息不单独渲染，通过 `tool_call_id` 挂到父 toolCall 下
- `content` 以 `System:` 开头 → `is_system: true`
- thinking 内容不返回

---

## 五、开发顺序

### Step 1：后端 API
- [ ] `GET /api/sessions`
- [ ] `GET /api/sessions/{session_key}/messages`
- [ ] `GET /` → 返回 index.html
- [ ] `GET /conversation.html` → 返回 conversation.html

### Step 2：会话列表页
- [ ] `static/index.html` + `static/js/index.js`
- [ ] 调用 `/api/sessions` 渲染列表

### Step 3：对话详情页
- [ ] `static/conversation.html` + `static/js/conversation.js`
- [ ] 从 URL 取 `id` 参数
- [ ] 调用 `/api/sessions/{id}/messages` 渲染消息流
- [ ] Tool Call 折叠交互
- [ ] 返回按钮

---

## 六、未来（不做）

以下功能留到以后：
- 仪表盘 / 统计卡片
- 每日趋势折线图
- 渠道分布饼图
- 筛选 / 搜索 / 分页
- Markdown 导出
- 增量解析

---

_文档版本：v0.2（简化版）_
_创建日期：2026-04-04_
