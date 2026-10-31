# count_word.py —— 代码统计工具

一个零依赖的小型命令行工具：遍历项目目录树，逐文件统计源码行数，按扩展名
分类，并按语言类型汇总。结果同时输出为 Markdown 与 CSV 两种报告。

```
$ python3 count_word.py /path/to/project
$ python3 count_word.py --help
```

## 环境要求

- Python 3.8+（仅使用标准库）。测试额外依赖 `pytest`，建议用 Python 3.10+ 运行。

## 用法

```
count_word.py [directory] [-o OUT] [-d {1,2,3}] [--include-empty] [--version]

  directory         源码树根目录（默认：当前目录）。
  -o, --output      报告输出目录。
                    默认：./code_stats/{project_name}（相对于当前工作目录）。
  -d, --depth       分类列的深度：1–3 层累积目录层级。
                    默认：1。
  --include-empty   同时列出不含非空白行的文件（记为 0 行）。
  --version         打印工具版本号后退出。
```

示例：

```bash
count_word.py                                  # 扫描当前目录 -> ./code_stats/default/
count_word.py ~/src/project                    # 扫描指定项目
count_word.py ~/src/project -o /tmp/reports    # 自定义输出目录
count_word.py ~/src/project -d 3               # 按 3 层目录分类
count_word.py ~/src/project --include-empty    # 报告中保留空文件
```

## 语义说明

- **行数统计**只统计*非空白行*。空行（完全为空或只含空白字符）不计入。文件最后
  一行没有换行符时也能正确处理（该残行仍算作一行）。
- **扫描范围**由扩展名的 glob 模式决定。默认集合覆盖 C / C++ / 头文件 / Python /
  shell；如需扩展，给 `CodeStatistics` 传入自己的 `extensions` 映射即可。
- **排除规则**
  - 文件模式（编译产物、系统元数据、编辑器交换文件等）匹配文件的 *basename*，
    命中即跳过。
  - 目录模式（`.git`、`build`、`dist`、`node_modules`、`__pycache__`、IDE 目录、
    CMake 构建目录等）匹配*任意层级的目录名*。被排除的目录在遍历过程中直接剪枝
    —— 其整棵子树都不会被进入，因此嵌套的 `build/`、`Debug/`、`out/` 等都会被忽略。
  - 当报告输出目录位于被扫描树*内部*时，它会被自动剪掉，从而保证工具永远
    不会统计自己上一次生成的报告。
- 默认**跳过非空白行为零的文件**；传入 `--include-empty`（或 `include_empty=True`）
  可把它们保留为 0 行记录。
- 无法读取的文件、无法列出内容的目录会向 stderr 打印 `[skip]` 警告后跳过，
  而不是中断整个运行。
- 不跟随符号链接目录，因此目录软链成环也不会让扫描卡死。

## 报告

两份报告都写入输出目录，文件名分别为 `{project_name_lower}_code_stats.md` 与
`..._csv`（CSV 采用带 BOM 的 UTF-8 编码，便于在表格软件中正常打开）。

- **Markdown** —— 先是 `# {project} -- Code Statistics` 汇总块（含按类型统计的
  表格），随后是逐文件明细表。
- **CSV** —— 一行表头，每个文件一行
  （`file_name, type, line_count, classify1, classify2, classify3, file_path`），
  最后一行是 `sum` 汇总标记行。

## 作为库使用

```python
from pathlib import Path
from count_word import CodeStatistics

stats = CodeStatistics(Path("~/src/project"), depth=2)
stats.scan()
stats.print_summary()
md  = stats.print_markdown()   # 同时返回 markdown 文本
stats.print_csv()
```

需要自定义统计范围时，给构造函数传入 `filter_files`、`filter_dirs` 和
`extensions`。

## 开发 / 测试

```bash
python3 -m pytest -q            # 在项目根目录运行全部测试
```

测试覆盖命令行端到端流程与库直接调用两种用法：输出路径逻辑、文件/行数统计、
任意层级的排除、空文件 / 纯空白文件 / 末尾无换行文件、符号链接成环、权限错误、
避免自扫描、深度分类以及命令行参数。

> `count_word.py` 中 `_FILTER_*` 系列默认过滤列表带有少量项目专属的历史痕迹
> （例如 `__init__.py`、`UI*`、某些第三方库目录名）。它们只是纯数据 —— 扫描
> 不适用的仓库时，可以随意删除或替换。
