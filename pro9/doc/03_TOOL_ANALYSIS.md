# OpenClaw 工具调用分析

> 基于 `summary.json`（2026-06-19 全天的 5 个会话统计）对 OpenClaw 工具体系的理解

---

## 一、当前数据概览

5 个会话共产生 **763 次工具调用**，但实际被用到的工具仅 **7 种**：

| 工具 | 调用次数 | 占比 |
|------|---------|------|
| `exec` | 296 | 38.7% |
| `read` | 217 | 28.4% |
| `edit` | 208 | 27.3% |
| `write` | 29 | 3.8% |
| `memory_search` | 2 | 0.3% |
| `update_plan` | 9 | 1.2% |
| `web_fetch` | 1 | 0.1% |

**结论：read / exec / edit 三项就占了 94.4% 的调用量。** 这个分布并非异常，而是由会话的任务性质决定的——会话内容集中在文件读写、代码开发、文本编辑上。

---

## 二、OpenClaw 内置工具全表

本表基于官方文档整理：

| 分组 | 工具 |
|------|------|
| 📁 **文件系统** | `read` `write` `edit` `apply_patch` |
| 💻 **运行时** | `exec` `process` `code_execution` |
| 🌐 **网络** | `web_search` `web_fetch` `x_search` |
| 🧠 **记忆** | `memory_search` `memory_get` |
| 🔁 **会话** | `sessions_list` `sessions_history` `sessions_send` `sessions_spawn` `sessions_yield` `subagents` `session_status` |
| 🖥️ **UI** | `browser` `canvas` |
| ⏰ **自动化** | `cron` `gateway` |
| 📱 **设备** | `nodes` |
| 🎵 **媒体** | `image` `image_generate` `music_generate` `video_generate` `tts` |
| 💬 **消息** | `message` |
| 📋 **其他** | `update_plan` |

### 插件扩展工具（需要安装插件）

| 插件 | 工具 |
|------|------|
| Diffs | `diffs` — diff 对比渲染 |
| LLM Task | `llm_task` — 结构化 JSON 输出 |
| Lobster | 可恢复的工作流审批 |
| OpenProse | Markdown 工作流编排 |
| Tokenjuice | 压缩 exec 输出 |

---

## 三、工具 vs 技能 vs 插件 架构

```
┌─────────────────────────────────────────────┐
│              能力层架构图                      │
│                                               │
│  工具 (Tools)    技能 (Skills)    插件 (Plugins) │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │ exec     │   │weather  │   │diffs     │  │
│  │ read     │   │health   │   │lobster   │  │
│  │ write    │ ←─│check    │ ←─│llm-task  │  │
│  │ browser  │   │taskflow │   │tokenjuice│  │
│  │ ...      │   │...      │   │...       │  │
│  └──────────┘   └──────────┘   └──────────┘  │
│       ↑              ↑              ↑         │
│  "我的手和脚"   "告诉我要怎么做"   "扩展能力"    │
└─────────────────────────────────────────────┘
```

### 核心区别

| | 工具 (Tool) | 技能 (Skill) | 插件 (Plugin) |
|---|---|---|---|
| **本质** | 可调用的函数 | 操作指南文档 | 可打包发布的扩展包 |
| **形式** | 结构化函数定义 | SKILL.md + 资源文件 | npm 包 |
| **能否被统计** | ✅ 每次调用都有记录 | ❌ 无记录 | ❌ 无独立记录 |
| **执行者** | 模型直接调用 | 指导模型调用工具 | 可注册新工具/渠道等 |
| **RPC 可见性** | ✅ 清晰可见 | ❌ 不可见 | ❌ 只通过其注册的工具体现 |

---

## 四、为什么当前只用到 7 种工具？

### 原因 1：任务类型决定工具分布

6 月 19 日的会话以 **知识协作、代码开发、内容生成** 为主，这类任务天然依赖：

- `read` → 阅读代码/文档/知识库
- `exec` → 运行命令验证想法
- `edit` / `write` → 生成和修改文件
- `update_plan` → 多步骤工作计划

### 原因 2：某些工具需要特定触发

一些工具在当前会话中从未被触发过，是因为没有对应的需求：

| 未使用的工具 | 需要什么才会触发？ |
|-------------|------------------|
| `browser` | "帮我在页面上填个表单"、"截图这个网页" |
| `image_generate` | "画一张图" |
| `music_generate` | "生成一段背景音乐" |
| `video_generate` | "生成一个短视频" |
| `cron` | "每天早上 9 点提醒我" |
| `web_search` | "搜索一下最近的热点" |
| `message` | 跨频道发送消息时 |
| `nodes` | 连接/管理配对的手机或设备 |

### 原因 3：部分工具有配置门槛

- `code_execution` 需要沙箱环境配置
- `browser` 需要 Chromium 实例
- `image_generate` / `music_generate` 需要对应 provider 的 API Key

---

## 五、数据洞察

### 5.1 缓存命中率极高

所有会话的 **缓存读取占比都在 97~98%**，说明 DeepSeek v4 的 KV Cache 机制非常成熟：

```
Session 5: 32,247,680 / 32,699,503 = 98.6% 缓存命中
Session 2: 24,358,016 / 24,855,607 = 98.0% 缓存命中
Session 3: 14,490,880 / 14,783,094 = 98.0% 缓存命中
```

### 5.2 输出/输入比合理

总输出 407K vs 总输入 1,448K，**输出/输入比 ≈ 28%**，属于 v4-flash 的典型表现（高输入低成本模型）。

### 5.3 工具错误率低

763 次调用中仅 18 次错误（2.4%），且分布在不同会话中，说明工具调用稳定性良好。

### 5.4 总成本极低

全天 5 个会话、1,794 条消息、763 次工具操作，总费用 **¥4.13**。

---

## 六、如果希望使用更多工具

当前配置下，如果需要激活更多工具，只需在对话中触发即可。以下是一些快速触发方式：

| 想用 | 可以说 |
|------|--------|
| `web_search` | "帮我搜索一下最近 XXX 的新闻" |
| `browser` | "打开这个网页看看" |
| `image_generate` | "帮我生成一张 XXX 的图片" |
| `cron` | "设置每天 8 点的提醒" |
| `web_fetch` | "抓取一下这个页面的内容" |
| `message` | 需要跨渠道发送时自动使用 |

---

## 七、深度解析：几个用得少的工具

### 7.1 `apply_patch` — 结构化多文件补丁

#### 它是什么

`apply_patch` 是一个专门用于**批量修改多个文件**的工具。它接受一个结构化的补丁字符串，可以一次完成新增文件、修改文件、删除文件、移动文件的操作。

#### 它和 `edit` 的区别

| | `edit` | `apply_patch` |
|---|---|---|
| 每次操作 | 只改一个文件的一段 | 一次改多个文件多个位置 |
| 格式 | 精确匹配 oldText → newText | 带标记的 patch 格式 |
| 原子性 | 单次调用单处修改 | 一次调用整个补丁 |
| 复杂度 | 适合小修改 | 适合跨文件的大修改 |

#### 语法示例

```
*** Begin Patch
*** Add File: path/to/new.txt
+line 1
+line 2
*** Update File: src/app.ts
@@
-old line
+new line
*** Delete File: obsolete.txt
*** End Patch
```

可以一次完成：新建 1 个文件 + 修改 2 个文件 + 删除 1 个文件。

_注：`apply_patch` 的路由依赖于 `tools.exec` 配置，当前模型（DeepSeek v4）不属于其默认启用范围（OpenAI/OpenAI Codex 模型才默认启用），这是它实际未被选用的一个技术原因。_

#### 什么场景会用到？

- **代码重构**：同时重命名变量、改多个引用、删旧文件
- **批量配置更新**：一次性修改多个配置文件的相同字段
- **代码生成**：生成完整项目时，一次写出多个骨架文件
- **跨文件迁移**：把一段逻辑从一个文件移到另一个文件

#### 为什么现在用得少？

当前会话的任务特点是**按需逐个修改**（改一段代码、写一个文件），还没遇到需要"一次改 5 个文件"的批量场景。另外它对模型有局限性——当前用的 DeepSeek v4 不属于默认启用 `apply_patch` 的模型范围。

---

### 7.2 `code_execution` — 远程沙箱 Python 分析

#### 它是什么

`code_execution` 运行在 **xAI 的远程沙箱**中，与本地 `exec` 不同：

| | `exec` | `code_execution` |
|---|---|---|
| 运行位置 | 你的机器或节点 | xAI 远程沙箱 |
| 可访问文件 | ✅ 本地文件系统 | ❌ 无本地文件访问 |
| 语言 | 任意 shell 命令 | Python 分析 |
| 适用场景 | 本地开发、运维 | 纯数据分析、计算 |

当前没有启用，原因很简单：**当前系统没有配置 xAI API Key**。配置位于：

```json5
{
  plugins: {
    entries: {
      xai: {
        config: {
          webSearch: { apiKey: "xai-..." },
          codeExecution: {
            enabled: true,
            model: "grok-4-1-fast",
            maxTurns: 2,
            timeoutSeconds: 30,
          },
        },
      },
    },
  },
}
```

需要先有 xAI 的 API Key 才能启用。

#### 什么场景会用到？

- **数据分析**：计算 7 日移动平均、统计分布、百分比变化
- **图表分析**：结合 `web_search` 获取数据后，在沙箱中绘图
- **纯计算**：大数运算、模拟、数值验证（不需要本地文件参与）
- **搭配搜索**：`x_search` 搜到推文后，`code_execution` 按天计数

#### 关键限制

- ❌ 不能访问本地文件
- ❌ 不能访问 workspace
- ❌ 不能调用终端环境
- ✅ 只能做纯 Python 分析 + 远程沙箱内计算

---

### 7.3 `process` — 后台进程管理器

#### 它是什么

`process` 是 `exec` 的**搭档工具**。当 `exec` 启动一个后台命令后，由 `process` 来管理它的生命周期：

exec (启动) ──→ 后台进程 ──→ process (管理)
                      │
                      ├─ poll:    查状态/看日志
                      ├─ log:     获取输出
                      ├─ write:   写入 stdin
                      ├─ send-keys: 发送按键 (tmux 风格)
                      ├─ paste:   粘贴文本
                      └─ kill:    终止进程

#### 有 process 和没有 process 的区别

**没有 process 时：**

每次 `exec` 调用都是一锤子买卖——发出命令，等最多 10 秒就超时转后台。返回一个 sessionId 后就失联了，无法知道后续状态。

```
你：帮我装个组件
exec(command="pip install xxx")
  → 3 秒后返回，但安装还在跑
我：超时了，不知道装完没有
  → 重新跑一次，又超时...
```

**有 process 时：**

`exec` 把任务扔到后台，`process` 在后面管着它。我不用一直守着——可以先去干别的事，想起来了就 poll 一下看看进度。

```
Step 1: exec 启动任务到后台
  → exec(command="pip install xxx", background=true)
  → 收到: {status: "running", sessionId: "s1"}

（30 秒后，去干别的事了回来）

Step 2: process 查进度
  → process(action="poll", sessionId="s1")
  → {status: "exited", output: "Successfully installed"}
```

#### 需要交互时更好理解

有 `process`，我可以在任务运行时中途输入，完成完整的人机交互流程：

```
Step 1: exec 启动到后台
  → exec(command="apt install mysql-server", background=true)
  → {status: "running", sessionId: "s1"}

Step 2: 看到需要确认
  → process(action="poll", sessionId="s1")
  → {output: "Do you want to continue? [Y/n] "}

Step 3: 发送按键回答
  → process(action="send-keys", sessionId="s1", keys=["y", "Enter"])
  → {output: "Proceeding with installation..."}

Step 4: 任务完成
  → process(action="poll", sessionId="s1")
  → {output: "Setup complete!", exitCode: 0}
```

#### 什么场景会用到？

- **长时间构建**：npm run build、make 等耗时任务
- **交互式 CLI**：需要回答 Yes/No 的命令
- **PTY 程序**：需要伪终端的 TTY 应用（vim、htop、ssh）
- **服务等待**：docker up 后等 ready，不断 check 日志
- **实时监控**：tail -f 跟踪日志输出

#### 为什么现在用得少？

从统计数据看，目前 296 次 `exec` 调用全是瞬时命令——跑一下就返回结果。没有出现过需要"启动一个长时间进程，然后不断回头看"的场景。

---

### 7.4 `memory_search` — 语义搜索记忆

#### 它是什么

`memory_search` 用**向量相似度 + 关键词**做混合检索，在我写的记忆文件中找到相关内容。即使措辞不同也能匹配。

```
向量搜索："gateway host" → 匹配 "the machine running OpenClaw"（意思相近）
关键词搜索："apply_patch" → 精确匹配文件名或函数名
```

两种方式各自搜一遍，加权合并后输出最优结果。

#### 它和 `memory_get` 的区别

| | `memory_search` | `memory_get` |
|---|---|---|
| 做什么 | 语义搜索，找相关片段 | 精确读取特定文件或行范围 |
| 匹配方式 | 向量 + 关键词混合 | 按文件名/行号精确定位 |
| 返回值 | 相关片段列表（含来源路径和分数） | 截取的文件内容 |
| 类比 | Google 搜索 | `cat` 命令 |

#### 我的记忆文件体系

我读写的记忆文件都在 workspace 根目录：

```
workspace/
├── MEMORY.md               # 长期记忆（每次主会话自动加载）
├── memory/
│   ├── YYYY-MM-DD.md        # 每日笔记（今天+昨天自动加载）
│   └── ...
└── HEARTBEAT.md             # 心跳任务清单
```

#### 需要 API Key 才能工作

`memory_search` 的语义搜索能力依赖一个 embedding 提供商（负责把文字转成向量）。支持：

| 提供商 | 是否需要 Key |
|--------|-------------|
| OpenAI | ✅ 需要 |
| Gemini | ✅ 需要 |
| Local（本地 GGUF 模型） | ❌ 不需要，但首次需下载 ~0.6GB 模型 |
| Ollama | ❌ 不需要 |

系统会自动检测已配置的 API Key 来启用。如果全部不可用，则降级为纯关键词匹配。

#### 使用场景

- **跨会话回忆**：你很久以前提过一个偏好，我不确定了 → `memory_search` 翻记忆
- **联想搜索**：你不知道确切文件名，但知道大概内容 → 语义匹配找出来
- **心跳自我检查**：我定期主动搜索记忆，看有没有该提醒你的事

#### 为什么现在用得少？

统计中 `memory_search` 只出现了 2 次，这完全正常：

1. **大部分记忆已经在上下文中** — MEMORY.md 每次会话自动加载，日常笔记（今天+昨天）也自动加载
2. **只有跨更久时间的回忆才需要它** — 比如你问"去年 12 月我们讨论过 XXX 吗？"才会触发
3. **当前会话集中在连续对话** — 同一个话题内连续聊，上下文里就有足够的信息

---

### 7.5 `memory_get` — 精确读取记忆片段

#### 它是什么

`memory_get` 是 `memory_search` 的搭档——搜到了相关文件后，用它精确提取想要的段落。可以指定文件名和行范围。

#### 对比

| | `read` | `memory_get` |
|---|---|---|
| 读取任意文件 | ✅ 是 | ❌ 只限记忆文件 |
| 按行范围截取 | ❌ 固定从某行读N行 | ✅ 可精确控制 |
| 自动截断/续传 | ✅ 有截断提示 | ✅ 有截断提示 |

#### 使用场景

- `memory_search` 返回了 3 个相关片段，看完整的原文
- 知道 MEMORY.md 的第 50-80 行是某个重要决定，直接读那段
- 查看今天的 daily note 某个特定部分

#### 完整工作流

```
Step 1: memory_search 发现线索
  → memory_search(query="git 操作规范")
  → 返回: {path: "MEMORY.md", snippet: "禁止执行任何 git 操作..."}

Step 2: memory_get 看全貌
  → memory_get(path="MEMORY.md", from=1, lines=50)
  → 返回完整上下文
```

#### 状态同步妙用

当 MEMORY.md 被其他进程修改后，我的上下文里可能还是旧版本。调用 `memory_get` 能重新从磁盘读取最新内容，保证读到的一定是最新的。

#### 为什么现在用得少？

同 `memory_search` — 2 次调用也合理。大部分时候需要的信息就在已加载的 MEMORY.md 里，不需要二次读取。

---

### 7.6 汇总：所有少用工具的原因分类

截至 6 月 19 日的数据，将少用的工具分为三类：

| 类别 | 包含工具 | 根本原因 |
|------|---------|---------|
| **模型限制** | `apply_patch` | 默认只对 OpenAI/Codex 模型启用，DeepSeek v4 不在范围内 |
| **未配置** | `code_execution` | 需要 xAI API Key，未配置 |
| **场景未触发** | `process`, `memory_search`, `memory_get`, `web_search`, `browser`, `cron`, `image_generate` 等 | 当前任务类型不需要它们 |

随着后续任务类型的扩展，这些工具的调用分布会自然变化。

---

### 7.7 会话管理工具组（session tools）

这组工具管理会话之间的通信、子代理的创建和状态查看。以下是 7 个工具的完整说明：

#### 7.7.1 `sessions_list` — 列出可见会话

**作用：** 按条件列出当前 OpenClaw 中可见的所有会话。用于发现有哪些会话还活着、可以交互或查阅历史。

**常用参数：** `kinds`（按类型过滤）、`label`（按标签）、`agentId`（按代理）、`activeMinutes`（最近活跃）、`search`（文本搜索）、`limit`（数量上限）。

**使用场景：**

- 想知道当前有多少活跃会话
- 找某个特定标签的群组会话
- 跨会话工作前，先列出可用的目标

#### 7.7.2 `sessions_history` — 读取会话历史

**作用：** 读取某个会话的完整对话历史（经过安全过滤）。

**安全过滤包括：**
- 移除 thinking 标签
- 剥离原始工具调用 XML
- 脱敏 credential/token 类文本
- 超长内容自动截断（含 oversized row 替换为 `[sessions_history omitted: message too large]`）
- 可能导致敏感信息泄露的历史对话被截断或整行替换

**常用参数：** `sessionKey`（目标会话）、`limit`（消息条数）、`includeTools`（是否包含工具调用记录）。

**使用场景：**

- 子代理跑完了，我去翻它的完整输出了什么
- 另一个会话里聊过某个话题，我想参考上下文
- 调试：查看某个长时间运行的会话里发生了什么

#### 7.7.3 `sessions_send` — 向其他会话发消息

**作用：** 向另一个会话发送消息，并可选等待回复。

**注意：** 不能向 Discord thread 发送（需发到父频道会话）。

**使用场景：**

- 子代理完成工作后，通过 `sessions_send` 通知主代理
- 跨会话协调：A 会话遇到阻塞，发消息给 B 会话请求处理
- 你同时和多个会话在聊天，我在 A 会话里把结果发到 B 会话

#### 7.7.4 `sessions_spawn` — 创建子代理（sub-agent）

**作用：** 创建一个独立的子会话，让它去后台执行一个任务，完成后自动把结果汇报回来。

**这是整个会话管理工具组里最核心的一个。**

**核心参数：**

| 参数 | 说明 |
|------|------|
| `task` | 交给子代理的任务描述（必填） |
| `label` | 可读标签（方便后续管理） |
| `model` | 可选，指定不同的模型（便宜的模型做简单任务） |
| `context` | `isolated`（默认，独立上下文）或 `fork`（复制当前对话上下文） |
| `runTimeoutSeconds` | 超时时间 |

**两种上下文模式：**

| 模式 | 适合场景 |
|------|---------|
| `isolated`（默认） | 独立研究、并行工作。我的当前对话内容不会传给子代理 |
| `fork` | 子代理需要知道我刚才在聊什么。比如我正在改一个项目，让子代理去查相关文档 |

#### 细化场景：并行分析多个项目

**串行（现在的做法）：**

```
你：帮我分析 pro7、pro8、pro9 三个项目

Round 1: 我读 pro7 所有文件 → 给你分析报告
         ← 等你回复
你：好的，继续

Round 2: 我读 pro8 所有文件 → 给你分析报告
         ← 等你回复
你：好的，继续

Round 3: 我读 pro9 所有文件 → 给你分析报告
→ 总耗时：3 轮对话交互
```

**并行（用 spawn 的做法）：**

```
你：帮我分析 pro7、pro8、pro9 三个项目

（同一时刻启动三个子代理）

T+0s:   子代理 1 → 读 pro7 文件
        子代理 2 → 读 pro8 文件
        子代理 3 → 读 pro9 文件

T+15s:  子代理 1 完成 → 结果自动推送到当前会话
T+20s:  子代理 3 完成 → 结果自动推送
T+25s:  子代理 2 完成 → 结果自动推送

→ 一次说完，三个结果陆续到账，无需中间交互
```

**关键差异：**

| | 串行无 spawn | 并行有 spawn |
|---|---|---|
| 耗时 | 任务数 × 单个耗时 | ≈ 最慢的任务耗时 |
| 你等待 | 每次做完要叫你继续 | 一次说完，结果自动回来 |
| 互不干扰 | 只能盯着做完一个 | 你可以聊别的，后台推送 |
| 上下文 | 同一个会话越积越大 | 每个子代理独立，用完销毁 |

**关键特性：**
- 非阻塞：调用后立即返回，不用等子代理跑完
- 推送通知：子代理完成后自动把结果发回当前会话
- 隔离安全：子代理默认看不到我的内存和会话列表
- 模型可选：复杂任务用好模型，简单任务用便宜的

#### 7.7.5 `sessions_yield` — 等待子代理结果

**作用：** 主动结束当前轮次，等待子代理返回结果后再继续。

**使用场景：**

```
# spawn 子代理后 yield 等结果
exec(command="pip install xxx")
sessions_spawn(task="跑测试用例")
sessions_yield()  # 主动让出，等子代理完成
  → 下一条消息就是子代理的汇报结果
```

**和 spawn 的区别：**

| | 纯 spawn | spawn + yield |
|---|---|---|
| 行为 | 非阻塞，立刻继续当前工作 | 阻塞等待，子代理完成后才继续 |
| 结果处理 | 子代理完成后推送通知 | 子代理结果作为下一条消息返回 |
| 场景 | 去干别的不急 | 我需要等这个结果才能继续 |

#### 7.7.6 `subagents` — 管理子代理

**作用：** 查看已创建的子代理状态、终止它们、或向它们发送指令。

**可用操作：**

| 操作 | 说明 |
|------|------|
| `list` | 列出当前会话创建的所有子代理 |
| `kill` | 终止特定的子代理 |
| `steer` | 向正在运行的子代理发消息（纠正方向/调整任务） |

**使用场景：**

- 子代理跑太久了，终止它 `kill target="run-123"`
- 子代理方向偏了，纠正它 `steer target="run-123" message="重点看安全性"`
- 看看还有哪些子代理在跑 `list`

#### 7.7.7 `session_status` — 查看当前会话状态

**作用：** 显示当前会话的 /status 卡片信息。也可以临时切换模型。

**信息包括：** 当前模型、token 用量和费用、会话时长、thinking level。

**使用场景：**

```
# 查看当前会话状态
session_status()
  → 显示：模型、token、费用等

# 临时切换模型
session_status(model="deepseek/deepseek-v4-flash")

# 恢复默认
session_status(model="default")
```

#### 汇总对比

| 工具 | 一句话说明 |
|------|-----------|
| `sessions_list` | 看看有哪些会话还在 |
| `sessions_history` | 翻某个会话的历史记录 |
| `sessions_send` | 跨会话发消息 |
| `sessions_spawn` | **派小弟去干活**（最核心） |
| `sessions_yield` | 等小弟干完再继续 |
| `subagents` | 管小弟（杀了/纠正/看状态） |
| `session_status` | 看我自己的状态/换模型 |

#### 为什么这些工具目前从未被调用？

从统计数据看，这 7 个工具的计数全部为 0。原因有三：

1. **当前一直是单一会话、直接对话** — 没有多会话协调的场景
2. **没有需要并行执行的任务** — 所有工作都是线性的：读→想→写→验
3. **子代理有成本** — 每个子代理是一个独立的模型调用，会增加 token 消耗

如果未来需要我同时做多件事（比如一边查资料一边写代码一边跑测试），这些工具就会自然用起来。

#### 触发关键词：怎么说能更容易触发 spawn

想让 spawn 子代理被自然触发，指令中带这些关键词更有效：

| 关键词 | 例子 |
|--------|------|
| 「**同时**」「**都**」「**分别**」 | 「帮我**同时**分析 A、B、C」「三个项目**都**看一下」「**分别**调研一下这几个方案」 |
| 「**对比**」「**各**」 | 「帮我**对比**三个方案」「看**各**目录的代码结构」 |
| 「**并行**」「**后台**」「**挂着**」 | 「这个**后台**跑着」「**并行**查一下」「帮我**挂着**编译」 |
| 「**放在一边**」「**回头再**」 | 「这个**放在一边**先」「**回头再**看结果」 |
| 明确罗列多个独立项目 | 「分析 pro7、pro8、pro9 的代码」「查 A 股、B 股、C 股的数据」 |
| 多个搜索/调研任务 | 「搜一下 HACS 最新版本，再看看 ESPHome 的更新日志」 |

**用一句话总结：** 一次让我做多件独立的事，spawn 就会自动被触发，把每件事拆成子代理并行执行。

---

## 附录：OpenClaw 文档存放位置

```
~/.nvm/versions/node/v24.14.0/lib/node_modules/openclaw/docs/
```

（完整路径：`/home/gtoo/.nvm/versions/node/v24.14.0/lib/node_modules/openclaw/docs/`）

### 目录结构

```
docs/
├── tools/          # 工具说明（本文主要参考来源）
│   ├── exec.md
│   ├── apply-patch.md
│   ├── code-execution.md
│   ├── browser.md
│   ├── web.md
│   ├── web-fetch.md
│   ├── image-generation.md
│   ├── subagents.md
│   ├── cron.md 等   ← 共 53 个文档
│   └── index.md    # 工具总览
├── gateway/        # Gateway 配置相关
├── concepts/       # 核心概念
├── plugins/        # 插件开发
├── cli/            # CLI 命令
├── security/       # 安全
├── providers/      # 模型提供商
├── automation/     # 自动化（cron/taskflow/hooks）
├── channels/       # 渠道配置
├── reference/      # 参考文档
├── web/            # Web 相关内容
├── start/          # 快速开始
├── install/        # 安装指南
├── platforms/      # 平台相关
├── assets/         # 媒体资源
├── images/         # 图片
├── snippets/       # 代码片段
├── help/           # 帮助文档
├── plan/           # 计划相关
├── nodes/          # 节点文档
├── debug/          # 调试
├── diagnostics/    # 诊断
└── ...其他
```

总大小约 **15MB**。

### 技能（Skills）存放位置

Skills 存放在独立的路径，与文档目录不在一起：

```
# 内置技能（社区发布的通用技能）
~/.nvm/versions/node/v24.14.0/lib/node_modules/openclaw/skills/
├── weather/
├── healthcheck/
├── skill-creator/
├── taskflow/
├── clawhub/
├── node-connect/
├── discord/        ← 共 50+ 个技能
└── ...

# 插件自带的技能（如浏览器自动化）
~/.openclaw/plugin-skills/
└── browser-automation/
```

### 如何直接阅读

```bash
# 查看某个工具的文档
cat ~/.nvm/versions/node/v24.14.0/lib/node_modules/openclaw/docs/tools/exec.md

# 查看所有可用技能
ls ~/.nvm/versions/node/v24.14.0/lib/node_modules/openclaw/skills/

# 查看某个技能的说明
cat ~/.nvm/versions/node/v24.14.0/lib/node_modules/openclaw/skills/weather/SKILL.md
```

### 文档来源速查

当我引用某个工具或功能的详细信息时，来源路径可以在对话中直接问我要：

- `docs/tools/xxx.md` → 工具使用说明
- `docs/gateway/xxx.md` → Gateway 配置
- `skills/xxx/SKILL.md` → 技能说明
- `docs/concepts/xxx.md` → 核心概念

---

*分析时间：2026-06-19*
*数据来源：openclaw_rpc_output/summary.json*
*文档来源：OpenClaw 内置官方文档 + Skills*
