# OpenClaw RPC 工具集

通过 Python 调用 RPC 接口与 OpenClaw Gateway 交互的脚本集合。

## 脚本列表

| 脚本 | 说明 |
|------|------|
| `session_stats.py` | 调取 `chat.history`，提取会话统计信息（不含对话正文），输出 JSON |

## 环境

```bash
conda activate openclaw_tool
```

依赖：`websockets`（已安装），其余均为 Python 3.8+ 标准库。

## 用法

```bash
python session_stats.py --token <token>
```

唯一必填参数是 token。

### 参数

| 参数 | 说明 |
|------|------|
| `--token` | **必需**。Gateway 认证 token |
| `--password` | Gateway 认证密码（二选一） |
| `--gateway` | Gateway 地址，默认 `ws://127.0.0.1:18789` |
| `--output` | 输出文件路径（默认自动生成 `session_stats_YYYYMMDD_HHMMSS.json`） |

### Token 获取方式

#### 方式一：从配置文件读取

`~/.openclaw/openclaw.json` 中的 `gateway.auth.token` 字段：

```bash
cat ~/.openclaw/openclaw.json | python3 -c "import sys,json; c=json.load(sys.stdin); print(c.get('gateway',{}).get('auth',{}).get('token',''))"
```

#### 方式二：CLI 命令

```bash
openclaw gateway token
```

#### 方式三：环境变量

设置后无需每次输入 `--token` 参数：

```bash
export OPENCLAW_GATEWAY_TOKEN="<你的token>"
```

### 示例

```bash
conda activate openclaw_tool

# 最基本用法
python session_stats.py --token "你的token"

# 指定输出文件
python session_stats.py --token "你的token" --output my_stats.json
```

### Session Key 获取方式

#### 方式一：从 Debug 面板 RPC 获取

1. 打开 **Control UI → Debug** 选项卡
2. 找到 **RPC** 调用区
3. 填入以下内容执行：

   - **方法**：`chat.history`
   - **参数**：`{ "sessionKey": "agent:main:dashboard:eae19d5d-8f0a-46e3-9e84-4e5d2d0e649e" }`

执行后返回的完整 JSON 中，在 `messages` 列表顶部或 `usage` 字段中能看到统计信息。

#### 方式二：从会话详情页 URL 获取

Control UI 中打开一个会话，浏览器地址栏 URL 中包含 session ID。

#### 方式三：从 JSONL 文件名获取

```bash
ls ~/.openclaw/agents/*/sessions/
```

文件名即 session ID，拼上 agent 前缀即为 session key。

### 修改默认会话

脚本顶部 `SESSION_KEY` 变量即会话 key，按需修改：

```python
SESSION_KEY = "agent:main:dashboard:eae19d5d-8f0a-46e3-9e84-4e5d2d0e649e"
```

## 相关文档

| 文档 | 内容 |
|------|------|
| `01_EXPORTER_DESIGN.md` | 会话统计脚本设计方案 |
| `02_RPC_QUERIES.md` | OpenClaw 常见 RPC 查询接口参考 |
| `03_TOOL_ANALYSIS.md` | OpenClaw 工具调用分析 |
| `04_DEEPSEEK_PRICING.md` | DeepSeek 官方定价参考 |

---

## 输出格式

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
