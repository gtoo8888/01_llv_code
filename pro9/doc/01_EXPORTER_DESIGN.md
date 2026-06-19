# LLM 会话统计脚本设计方案

## 1. 需求

一个简单的 Python 脚本：

1. 通过 RPC 调用 `chat.history` 获取会话数据
2. 解析返回的 JSON，**丢弃长对话正文**
3. 只提取基础的统计信息
4. 输出为 **JSON**

不做复杂架构，不做多格式支持，不输出对话原文。

## 2. Python 环境

```bash
# 1. 激活 conda 环境
conda activate openclaw_tool

# 2. 确认环境
python --version              # Python 3.8+
python -c "import websockets; import json; import argparse; import asyncio"  # 无报错即就绪
```

- **环境名**：`openclaw_tool`（conda）
- **依赖**：`websockets` 已安装，无需额外 pip
- **标准库**：`json`、`argparse`、`datetime`、`asyncio` 均为 Python 3.8+ 内置
- **运行前务必激活环境**：`conda activate openclaw_tool`

## 3. 命令行接口

```bash
python3 session_stats.py --session <sessionKey> [options]

# 最简单用法（Gateway 在本地 18789，无 token）
python3 session_stats.py --session agent:main:dashboard:xxx

# 输出到文件
python3 session_stats.py --session agent:main:dashboard:xxx --output stats.json

# 远程 Gateway + 需要 token
python3 session_stats.py \
  --session agent:main:dashboard:xxx \
  --gateway ws://192.168.1.100:18789 \
  --token my_gateway_token
```

只有一个子命令 `export`（默认行为），没有 `list`、没有 multi-format。

## 4. 输出 JSON 格式

```json
{
  "session_id": "agent:main:dashboard:xxx",
  "exported_at": "2026-06-19T17:30:00+08:00",
  "statistics": {
    "model": "deepseek-v4-flash",
    "duration": {
      "start": "2026-06-19T00:56:38+08:00",
      "end": "2026-06-19T03:16:20+08:00",
      "seconds": 8382,
      "readable": "2h 19m"
    },
    "messages": {
      "total": 139,
      "user": 48,
      "assistant": 55,
      "tool_result": 36
    },
    "tool_calls": {
      "total": 229,
      "distinct_tools": 4,
      "distribution": {
        "read": 79,
        "exec": 75,
        "edit": 66,
        "write": 9
      },
      "errors": 0
    },
    "tokens": {
      "total": 32700000,
      "input": 328900,
      "output": 122900,
      "cache_write": 0,
      "cache_read": 32200000
    },
    "cost_usd": 0.98
  }
}
```

## 5. 代码结构（极简）

```
pro9/
├── session_stats.py         # 唯一脚本（主入口 + RPC 调用 + 解析 + JSON 输出）
├── requirements.txt         # websockets>=13.0
└── README.md                # 使用说明
```

- `session_stats.py` 是整个脚本，包含所有逻辑
- 如果需要做单元测试，拆分出一个 `stats.py` 存放统计函数

## 6. 内部流程

```
1. argparse 解析参数（--session, --gateway, --token, --output）

2. 连接 Gateway WebSocket
   ws://<gateway_host>:<gateway_port>
   如果提供了 token，在连接 param 中携带认证

3. 发送 RPC 请求
   方法: chat.history
   参数: { "sessionKey": "<sessionKey>" }

4. 接收完整 JSON 响应

5. 从响应中提取统计信息
   - 消息总数 = messages 数组长度
   - 分角色计数 = 遍历 messages，按 role 分组
   - 工具调用统计 = 遍历 assistant 消息，统计 tool_calls 中的 function.name
   - 时间范围 = messages 首尾的 createdAt
   - Token 用量 = 尝试从响应元数据中提取（如 usage 字段）；若无则从消息内容估算
   - 费用 = token × 模型单价

6. 输出 JSON
   json.dumps(statistics, indent=2, ensure_ascii=False)
   写入 stdout 或 --output 指定的文件
```

## 7. 不做什么

- ❌ 不输出对话原文（每条消息的 content 字段仅用于统计 token，不写入结果）
- ❌ 不做 Markdown / 终端表格输出
- ❌ 不做批量 list 模式
- ❌ 不做 JSONL 文件读取（只走 RPC）
- ❌ 不拆分多模块（一个脚本搞定）
