# 工具接入

> 说明夜莺如何把外部工具接入运行环境，供开发子代理在干活时使用。本文定义工具的三种形态、配置方式、自检流程、以及子代理如何获知可用工具。核心原则：**自检失败就标记失败，不尝试安装或修复；可用则直接开放给子代理，细节由子代理自行查阅文档。**

## 一、工具形态

夜莺支持三种工具形态，覆盖绝大多数开发场景：

| 形态 | 调用方式 | 示例 | 自检方式 |
|---|---|---|---|
| `command` | 直接执行命令行指令 | readtags、ripgrep、doxygen | 执行一个最小命令（如 `--version`），看退出码 |
| `mcp` | 通过 MCP 服务调用 | codegraph | 执行一次最小 MCP 调用（如健康检查或简单查询） |
| `skill` | 作为 skill 被平台加载调用 | understand-anything | 检查 skill 目录及入口文件存在且可读 |

三种形态覆盖了从直接命令到结构化服务到知识型技能的不同粒度。未来新增工具只需在配置中增加条目并指明 `type`，无需改动自检框架。

## 二、工具清单

夜莺默认接入一批以**静态代码搜索、理解、文档生成为主**的工具（Python 因为运行方便，开放给子代理直接使用），覆盖 `command` / `mcp` / `skill` 三种形态（见 §一）。默认清单及收录理由概览如下：

| 工具 | 形态 | 用途与收录理由 | 关键 |
|---|---|---|---|
| `git` | command | 版本控制；commit 审计与每日复盘的前提 | **是** |
| `python3` | command | Python 运行时；pip 和 unittest 的前提 | **是** |
| `pip` | command | Python 包管理 | 是 |
| `readtags` | command | 基于 tags 索引的符号查询 | 否 |
| `ctags` | command | 生成 tags 索引文件（readtags 的前提） | 否 |
| `cscope` | command | C 代码交叉引用查询 | 否 |
| `ripgrep` | command | 快速全文搜索 | 否 |
| `curl` | command | 网络请求、下载依赖 | 否 |
| `npm` | command | Node 包管理，拉取杂项包 | 否 |
| `unittest` | command | Python 单元测试框架（标准库，随 python3 附带） | 否 |
| `doxygen` | command | 从注释生成文档 | 否 |
| `codegraph` | mcp | 代码图查询，跨语言 | 否 |
| `understand-anything` | skill | 深度代码理解 | 否 |

> 本表与 `references/config.template.json` 的 `tools.items` 保持一致（顺序同源）；增删默认工具请两处同步。每条工具的自检命令（`check`）属于机器细节，见该文件，本文不重复。

**关键工具**（`git`、`python3`、`pip`）自检失败时终止启动；**非关键工具**失败只标记不可用，不阻塞（见 §四、§六）。

**明确不开放的能力**：编译器（gcc/g++/clang）、构建系统（make/cmake）、clang 系列静态分析/格式化工具（clang-tidy、clang-format）。原因：这些工具在不同平台上的安装和版本差异较大，且涉及实际编译构建，夜莺当前只做静态层面的代码搜索、理解和文档生成。

## 三、配置结构

工具清单写入 `state/config.json` 的 `tools` 字段，结构为 `tools.items` 数组，每条目含 `name / type / check / required / note` 五个字段，语义见下表。默认条目构成与用途概览见 §二；各条的完整取值（含 `check` 自检命令）以 `references/config.template.json` 的 `tools` 字段为准，本文不重复完整 JSON。

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 工具标识名，自检结果和 prompt 注入时使用 |
| `type` | enum | `command` / `mcp` / `skill` |
| `check` | string | 自检方式；`command` 类型为 shell 命令，`mcp` 类型为 MCP 调用描述，`skill` 类型为目录路径或检测指令 |
| `required` | boolean | `true` 表示关键工具，自检失败时终止启动 |
| `note` | string | 一句话用途说明 |

用户启动夜莺时可根据项目实际情况增删条目。清单不必固定为上述内容，以 `state/config.json` 实际写入为准。

## 四、环境自检流程

启动时，Loop 遍历 `tools.items` 数组，按 `type` 执行相应自检，将结果写入 `state/env_check.json`。

### command 类型

执行 `check` 指定的命令，根据退出码判断：

- 退出码为 0 → `ok`
- 退出码非 0 或命令不存在 → `fail`
- 执行超时（如超过 5 秒无响应）→ `fail`

**不尝试安装缺失的工具**。失败就标记失败，后续轮次中该工具被视为不可用。

### mcp 类型

执行一次最小 MCP 调用。`check` 字段指定调用内容（如 `codegraph.ping` 或查询一个已知节点）。返回正常 → `ok`；调用失败、超时或服务不可达 → `fail`。

### skill 类型

检查 skill 是否可加载：

- skill 目录存在
- 入口文件（如 `SKILL.md`）存在且可读

两者都满足 → `ok`；否则 → `fail`。

### 结果落盘

`state/env_check.json` 结构：

```json
{
  "checked_at": "<ISO 时间>",
  "results": [
    {
      "name": "python3",
      "status": "ok",
      "note": "python3 --version 正常"
    },
    {
      "name": "doxygen",
      "status": "fail",
      "note": "command not found: doxygen"
    }
  ],
  "critical_ok": true
}
```

- `results`：每项工具的自检结果，`status` 取值 `ok / fail / skipped`（`skipped` 表示该条目本轮未执行检测，如被暂时禁用或平台不支持），`note` 记录成功说明或失败原因。
- `critical_ok`：只要有一个 `required: true` 的工具 `fail` 则为 `false`，启动应终止。

## 五、可用工具注入 prompt

自检完成后，可用工具不单独由驱动方拼——`scripts/schedule_mode.py` 会从 `state/env_check.json` 读出所有 `status == "ok"` 的工具名（排除 `im_*` 渠道项），并入它输出的 `args.tools`；驱动方把该 `args` 段原样传给 `nightingale_cycle.js`，由脚本动态拼进开发子代理 prompt。无 Workflow 驱动的后备手工模式则由子代理先自读 `env_check.json` 决定可用集。拼接提示格式如下：

```
本轮可用工具：git, python3, pip, readtags, ctags, cscope, rg, curl, npm, unittest, doxygen, codegraph, understand-anything
```

**只列工具名，不提供详细用法。** 子代理拿到工具名后自行查阅文档或通过 `--help` 等方式探索用法。工具本身文档详实，无需在 prompt 中重复。

如果某工具自检失败，则不出现在列表中，子代理自然不会尝试使用。这样：

- 工具清单变化时，只需更新 `config.json` 和重新自检，不用改 prompt 模板。
- 不同运行环境（如 Windows 与 Linux）可以有不同工具集，子代理始终清楚当前环境有什么可用。

## 六、失败策略

**一句话原则：失败不用，不修不装。**

- 非关键工具 `fail` → 仅标记不可用，该工具不出现在可用工具列表中，不影响夜莺启动和运行。
- 关键工具 `fail` → 报告用户并终止启动（关键工具当前为 `git`、`python3` 和 `pip`）。
- 运行过程中不尝试自动安装、下载或修复任何工具。
- 如果某轮开发确实需要某个不可用的工具，子代理应选择替代方案（如用 `rg` 代替 `readtags` 做搜索），或将需求写入 commit message / 评估结果，由次日人工审查时决定是否安装。

## 七、边界与不做什么

夜莺的工具接入遵循以下边界：

1. **不开放编译构建**：不接入编译器（gcc/g++/clang）、构建系统（make/cmake）、链接器等。夜莺只做静态层面的代码搜索、理解、文档生成。
2. **不自动安装**：自检失败不尝试 pip/npm/apt 等任何安装操作。这是为了保持夜莺行为可预测、不引入不可控的网络和权限操作。
3. **不注入详细用法**：工具用法由子代理自行查阅，避免 prompt 臃肿和配置冗余。
4. **不硬编码工具集**：工具清单以 `state/config.json` 为准，模板只提供默认样例。用户可根据项目裁剪。

