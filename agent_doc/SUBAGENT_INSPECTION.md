# 子代理（Subagent）过程查询指南

## 概述

当 Claude 启动多代理工作流（如 `/deep-research`）时，每个子代理的执行记录会保存到磁盘。本文档说明如何查看这些记录。

## 存储位置

```
<session-dir>/subagents/workflows/<run-id>/
```

实例如：

```bash
# 用最近一次为例
ls -la /home/gtoo/.claude/projects/-data-sdb-openclaw-KnowledgeWorkspace-02-llv-generated-01-llv-code/8b2b9b55-050f-4d73-92b9-eb565b1aa021/subagents/workflows/
```

其中 `run-id` 格式为 `wf_xxxxxxxx-xxx`，每个 `run-id` 即一次 Workflow 调用。

## 目录结构

```
<run-id>/
├── journal.jsonl              ← 工作流日志（核心！结构化记录了每个阶段的起止）
├── agent-<hash>.jsonl         ← 子代理的完整对话记录
├── agent-<hash>.meta.json     ← 子代理元数据（{"agentType":"...", "spawnDepth":1}）
├── agent-<hash>.jsonl
├── agent-<hash>.meta.json
└── ...
```

## 核心文件解析

### 1. journal.jsonl — 工作流进度日志

这是最重要的文件，JSONL 格式，每行一个事件。关键事件类型：

| type | 含义 | 关键字段 |
|------|------|---------|
| `started` | 子代理启动 | `agentId`、`key` |
| `result` | 子代理返回结果 | `agentId`、`result`（包含该代理的结构化产出） |
| `phase` | 阶段切换 | `phase`（阶段名） |

查看所有已完成代理及其产出：

```bash
# 查看每个 result 的精要
grep '"type":"result"' journal.jsonl | python3 -c "
import json, sys
for line in sys.stdin:
    d = json.loads(line.strip())
    r = d.get('result', {})
    agent = d['agentId'][:12]
    if 'summary' in r:
        print(f'✦ {agent} → 范围界定: {r[\"summary\"][:80]}...')
        for a in r.get('angles', []):
            print(f'  ├ {a[\"label\"]}: {a[\"query\"]}')
    elif 'results' in r:
        urls = len(r['results'])
        print(f'✦ {agent} → 搜索: 找到 {urls} 个结果')
    elif 'claims' in r:
        c_count = len(r['claims'])
        print(f'✦ {agent} → 提取: {c_count} 个 claim (质量: {r.get(\"sourceQuality\",\"?\")})')
        for c in r['claims'][:3]:
            print(f'  ├ [{c[\"importance\"]}] {c[\"claim\"][:60]}...')
    elif 'sourceQuality' in r:
        print(f'✦ {agent} → 提取: 质量={r[\"sourceQuality\"]} (无有效 claim)')
    else:
        keys = list(r.keys())[:5]
        print(f'✦ {agent} → 其他: keys={keys}')
"
```

### 2. agent-<hash>.jsonl — 子代理完整对话

每个子代理的完整会话记录，包含：
- 系统提示词
- 用户指令
- 工具调用与结果
- 最终输出

查看某个子代理的关键内容：

```bash
# 查看某个 agent 的类型
cat agent-<hash>.jsonl | python3 -c "
import json, sys
for line in sys.stdin:
    d = json.loads(line.strip())
    t = d.get('type', '')
    msg = d.get('message', '')
    if t == 'user':
        print(f'┌─ 用户指令 ({len(msg)} chars):')
        print(f'│  {msg[:200]}...' if len(msg)>200 else f'│  {msg}')
    elif t == 'tool_use':
        name = d.get('tool_use', {}).get('name', '')
        print(f'├─ 工具调用: {name}')
    elif t == 'tool_result':
        result = d.get('message', '')
        print(f'├─ 工具结果 ({len(result)} chars)')
    elif t == 'assistant_response':
        print(f'└─ 最终回复 ({len(msg)} chars):')
        print(f'   {msg[:200]}...' if len(msg)>200 else f'   {msg}')
"
```

### 3. agent-<hash>.meta.json — 子代理元数据

简单的 JSON，标明类型和层级：

```json
{"agentType":"workflow-subagent","spawnDepth":1}
```

## 常用查询命令

### 查看工作流整体概览

```bash
cd <run-id>/

# 一共多少个子代理
ls *.jsonl | grep -v journal | wc -l

# 总磁盘大小
du -sh .

# 最大的 agent 是哪个（最耗资源的）
ls -lhS *.jsonl | head -5

# 看哪些 agent 已经完成了
grep '"type":"result"' journal.jsonl | wc -l

# 看哪些 agent 失败了/没产出
grep '"type":"result"' journal.jsonl | python3 -c "
import json, sys
for line in sys.stdin:
    d = json.loads(line.strip())
    r = d.get('result', {})
    if isinstance(r, str):
        print(f'{d[\"agentId\"][:12]} → 失败: {r[:80]}')
    elif 'error' in r:
        print(f'{d[\"agentId\"][:12]} → 错误: {r[\"error\"]}')
"
```

### 查看某一阶段所有 agent

```bash
# 使用 journal 的时间戳 + agentId 推断阶段
grep '"type":"result"' journal.jsonl | python3 -c "
import json, sys
for line in sys.stdin:
    d = json.loads(line.strip())
    r = d.get('result', {})
    agent = d['agentId'][:12]
    if 'results' in r:
        print(f'[SEARCH]  {agent}: {len(r[\"results\"])} URLs')
    elif 'claims' in r:
        print(f'[FETCH]   {agent}: {len(r[\"claims\"])} claims ({r.get(\"sourceQuality\",\"\")})')
    elif 'angles' in r:
        print(f'[SCOPE]   {agent}: {r[\"summary\"][:50]}')
"
```

## 消耗统计

### 快速统计资源消耗

```bash
# 总字数 → 按 3 chars/token 估算 token 消耗
du -sb . && echo "≈ $(du -sb . | cut -f1)/3 ≈ $(( $(du -sb . | cut -f1) / 3 )) tokens"

# 每个 agent 的字数排行
for f in *.jsonl; do
  chars=$(wc -c < "$f")
  echo "$chars $f"
done | sort -rn | head -10 | awk '{printf "%6.1f KB  %s\n", $1/1024, $2}'
```

## 注意事项

- **agent-<hash>.jsonl 文件是完整的对话日志**，包含系统提示词和工具调用细节，不要直接 cat 到上下文 —— 它会撑爆窗口
- 查询时优先用 `journal.jsonl`，它是结构化摘要
- 已停止的工作流文件不会被删除，数据仍在磁盘上
- 每个子代理的实际 token 消耗**不在 metadata 中**，需要从 jsonl 内容的字符数估算
