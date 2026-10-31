# -*- coding: utf-8 -*-
"""
代码统计工具 —— 统计行数、按扩展名分类、按语言类型汇总。

语义 / 行为
-----------
* **行数统计**：只统计**非空白行**，即空行（完全为空或只含空白字符）不计入
  文件的行数。文件最后一行没有换行符时也能正确处理（末尾的残行算作一行）。
* **扫描范围**：完全由扩展名模式决定（见 ``_DEFAULT_EXTENSIONS``）：只有当文件的
  basename（文件名）匹配某个已配置的 glob 模式时，该文件才会被统计。
* **排除规则**：文件模式（二进制文件、系统元数据、编辑器备份）匹配的是**文件名**；
  目录模式（版本控制目录、IDE 目录、构建/缓存目录）匹配的是**任意层级的目录名**，
  命中的目录会被整体剪枝（其整棵子树永远不会被进入）。
* 默认**跳过非空白行数为零的文件**（传入 ``--include-empty`` 可保留为 0 行的记录）。
* 报告默认写入被扫描树**之外**的目录；若输出目录位于被扫描树内部，遍历时会把
  它剪掉，以免工具统计自己上一次生成的报告。

兼容 Python 3.8+（使用标准库的 dataclasses 与 typing 泛型）。最低支持版本为
Python 3.8，不依赖任何外部库。
"""

from __future__ import annotations

import argparse
import csv
import datetime
import fnmatch
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

__version__ = "1.0.0"

# 默认输出子目录名（仅当直接调用 CodeStatistics 时使用）
_DEFAULT_OUTPUT_DIR = "code_stats"

# 终端输出用的 ANSI 颜色码
_C_GREEN = "\033[92m"
_C_CYAN = "\033[96m"
_C_YELLOW = "\033[93m"
_C_RED = "\033[91m"
_C_RESET = "\033[0m"

# 需要跳过的文件模式（glob 风格通配符，匹配文件的 basename 文件名）。
# 这些是本工具的主观默认值；传入 filter_files 可覆盖。
_FILTER_LANG_BUILD: List[str] = [
    "*.pyc", "*.pyo",
    "*.o", "*.obj",
    "*.a", "*.so", "*.dll", "*.lib", "*.exe",
    "*.out",
]

_FILTER_IDE_OS: List[str] = [
    ".DS_Store", "Thumbs.db",  # 操作系统元数据
    "*~", "*.swp", "*.swo",   # 备份文件 / vim 交换文件
]

_FILTER_BUILD_ARTIFACTS: List[str] = [
    "CMakeCache.txt",
]

_FILTER_PROJECT_SPECIFIC: List[str] = [
    "UI*", "__init__.py",
    "Chat1.md", "cJSON.c",
]

_DEFAULT_FILTER_FILES: List[str] = (
    _FILTER_LANG_BUILD + _FILTER_IDE_OS
    + _FILTER_BUILD_ARTIFACTS + _FILTER_PROJECT_SPECIFIC
)


# 需要跳过的目录模式（glob 风格，匹配**任意层级**的目录名 —— 命中即在遍历
# 过程中剪枝整棵子树）。这些是本工具的主观默认值；传入 filter_dirs 可覆盖。
_FILTER_VERSION_CONTROL: List[str] = [
    ".git", ".svn", ".hg",
]

_FILTER_IDE_DIRS: List[str] = [
    ".vscode", ".idea", ".vs",
]

_FILTER_CACHE: List[str] = [
    "__pycache__", "node_modules",
]

_FILTER_BUILD_DIRS: List[str] = [
    "build", "dist", "bin", "out",
    "cmake-build-*",
    "Debug", "Release", "RelWithDebInfo", "MinSizeRel",
    "x64", "x86", "Win32", "ARM64", "ARM",
]

_FILTER_QT: List[str] = [
    "moc_*", "qrc_*",
]

_FILTER_UNIT_TEST: List[str] = [
    "UnitTest*",
]

_FILTER_SPECIAL: List[str] = [
    "webbench-1.5", "brandy", "ori_compile",
    "coroutine_lib_gtoo", "new_src", "dbow3",
    "third_ros*", "pcl_learn*",
]

_DEFAULT_FILTER_DIRS: List[str] = (
    _FILTER_VERSION_CONTROL + _FILTER_IDE_DIRS + _FILTER_CACHE + _FILTER_BUILD_DIRS + _FILTER_QT + _FILTER_UNIT_TEST
    + _FILTER_SPECIAL
)

# 扩展名 → 类型映射（每个 key 都是匹配文件 basename 的 glob 模式；
# 第一个命中的模式决定该文件的语言类型）
_DEFAULT_EXTENSIONS: Dict[str, str] = {
    "*.c":         "C",
    "*.cc":        "C++",
    "*.cxx":       "C++",
    "*.cpp":       "C++",
    "*.h":         "C/C++ Header",
    "*.h++":       "C++ Header",
    "*.hpp":       "C++ Header",
    "*.py":        "Python",
    "*.sh":        "Script",
    # 如需统计以下类型，取消注释即可
    # "*.md":      "Markdown",
    # "CMake*":    "Build",
    # "Make*":     "Build",
    # ".gitlab-ci.yml": "CI",
}

@dataclass
class CodeEntry:
    """单个匹配到的源文件的统计信息。"""
    file_name: str = ""
    file_type: str = ""
    line_count: int = 0
    classify1: str = ""
    classify2: str = ""
    classify3: str = ""
    relative_path: str = ""

    def to_csv_row(self) -> List:
        return [self.file_name, self.file_type, self.line_count,
                self.classify1, self.classify2, self.classify3, self.relative_path]

    def to_markdown_row(self) -> str:
        escaped = self.relative_path.replace("|", "\\|")
        return f"| {self.file_name} | {self.file_type} | {self.line_count} | {self.classify1} | {self.classify2} | {self.classify3} | {escaped} |\n"

class CodeStatistics:
    def __init__(
        self,
        input_dir: Path,
        output_dir: Optional[Path] = None,
        depth: int = 1,
        filter_files: Optional[List[str]] = None,
        filter_dirs: Optional[List[str]] = None,
        extensions: Optional[Dict[str, str]] = None,
        include_empty: bool = False,
    ):
        self.input_dir: Path = input_dir.resolve()
        self.output_dir: Path = (output_dir or input_dir / _DEFAULT_OUTPUT_DIR).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.depth: int = depth
        self.filter_files: List[str] = filter_files or list(_DEFAULT_FILTER_FILES)
        self.filter_dirs: List[str] = filter_dirs or list(_DEFAULT_FILTER_DIRS)
        self.extensions: Dict[str, str] = extensions or dict(_DEFAULT_EXTENSIONS)
        # 为 True 时，可读但非空白行数为零的文件仍会出现在报告中
        # （行数记为 0）。
        self.include_empty: bool = include_empty

        self.project_name: str = self.input_dir.name
        self.entries: List[CodeEntry] = []

        self.total_files: int = 0
        self.total_lines: int = 0
        self.type_counts: Dict[str, int] = defaultdict(int)       # 每种类型的文件数
        self.type_lines: Dict[str, int] = defaultdict(int)        # 每种类型的行数

    @staticmethod
    def _count_lines(file_path: Path) -> Optional[int]:
        """统计 ``file_path`` 中的非空白行数。

        文件无法读取时返回 ``None``（同时向 stderr 打印警告），这样调用方就能
        区分*不可读*与*空文件*两种情形。
        """
        try:
            with open(file_path, "rb") as f:
                return sum(1 for line in f if line.strip())
        except OSError as exc:
            print(f"  [skip] unreadable file: {file_path} -- {exc}", file=sys.stderr)
            return None

    def _file_type_of(self, name: str) -> Optional[str]:
        """返回 ``name`` 对应的语言类型；若该文件不参与统计则返回 ``None``。

        当文件的 basename 匹配某个已配置的扩展名 glob 模式时，它被视为源文件，
        且第一个命中的模式生效。
        """
        for pattern, file_type in self.extensions.items():
            if fnmatch.fnmatch(name, pattern):
                return file_type
        return None

    @staticmethod
    def _classify_levels(rel_path: str, depth: int = 1) -> tuple[str, str, str]:
        """取出最多 3 层累积目录层级；缺失的层级回退到上一层。"""
        parts = Path(rel_path).parent.parts    # 去掉文件名，只保留目录
        # 根目录下的文件：parent 为 "." → parts = () → 置为 ("root",)
        if not parts:
            parts = ("root",)
        c1 = parts[0] if len(parts) > 0 else ""

        if len(parts) > 1:
            c2 = "/".join(parts[:2])
        else:
            c2 = c1  # 回退到上一层

        if len(parts) > 2:
            c3 = "/".join(parts[:3])
        else:
            c3 = c2  # 回退到上一层

        if depth < 2:
            c2 = ""
        if depth < 3:
            c3 = ""
        return c1, c2, c3

    def _is_excluded_file(self, name: str) -> bool:
        return any(fnmatch.fnmatch(name, pat) for pat in self.filter_files)

    @staticmethod
    def _is_excluded_dir_name(name: str, patterns: List[str]) -> bool:
        """当目录 ``name`` 命中任一排除模式时返回 True。

        目录模式匹配的是**目录名（basename）**，因此排除在**任意嵌套层级**都生效
        （无论 ``build/`` 或 ``node_modules/`` 位于项目根目录还是往下五层，都会被
        剪枝）。
        """
        return any(fnmatch.fnmatch(name, pat) for pat in patterns)

    def _prune_dir(self, rel_parts, out_parts) -> bool:
        """决定遍历时是否要进入某个目录。

        ``rel_parts`` 是该目录相对 ``input_dir`` 的路径分量。以下两种情况会被剪枝：
        (a) 该目录是报告输出目录或其子孙目录（遍历首次到达输出目录时即剪枝，因此
        其整棵子树都被跳过）；(b) 其目录名命中某个已配置的目录排除模式。
        """
        if out_parts is not None and rel_parts[:len(out_parts)] == out_parts:
            return True
        return self._is_excluded_dir_name(rel_parts[-1], self.filter_dirs)

    def scan(self) -> None:
        """遍历输入目录并收集统计信息。

        遍历时**边下探边剪枝**，因此排除在任意层级都有效，``build/``、``.git/``、
        ``node_modules/`` 等被排除的子树永远不会被进入。无法列出内容的目录会打印
        警告后跳过，而不是中断整个运行；符号链接目录不会被跟随（软链成环也不会
        让扫描卡死）。
        """
        self.entries.clear()
        self.total_files = 0
        self.total_lines = 0
        self.type_counts.clear()
        self.type_lines.clear()

        input_dir = self.input_dir

        # 报告输出目录若位于被扫描树内部，就不能遍历它，否则工具会把
        # 自己上一次生成的报告也统计进来。
        out_parts: Optional[tuple] = None
        try:
            out_parts = self.output_dir.resolve().relative_to(input_dir).parts
        except ValueError:
            out_parts = None

        def onerror(exc: OSError) -> None:
            print(f"  [skip] cannot list directory: {exc}",
                  file=sys.stderr)

        for dirpath, dirnames, filenames in os.walk(
            input_dir, topdown=True, followlinks=False, onerror=onerror,
        ):
            dir_path = Path(dirpath)
            try:
                rel_parts = dir_path.relative_to(input_dir).parts
            except ValueError:
                rel_parts = ()

            # 就地剪掉被排除的目录（永不进入它们）。
            kept_dirs = []
            for name in sorted(dirnames):
                if self._prune_dir(rel_parts + (name,), out_parts):
                    continue
                kept_dirs.append(name)
            dirnames[:] = kept_dirs

            for file_name in sorted(filenames):
                # 按文件名模式跳过（二进制文件 / 系统元数据 / 编辑器残留文件）。
                if self._is_excluded_file(file_name):
                    continue

                file_type = self._file_type_of(file_name)
                if file_type is None:
                    continue  # 不是已配置的源码扩展名

                file_path = dir_path / file_name
                lines = self._count_lines(file_path)
                if lines is None:
                    continue  # 文件不可读 —— 已在 stderr 上警告过
                if lines == 0 and not self.include_empty:
                    continue

                rel = file_path.relative_to(input_dir).as_posix()
                c1, c2, c3 = self._classify_levels(rel, self.depth)

                entry = CodeEntry(
                    file_name=file_name,
                    file_type=file_type,
                    line_count=lines,
                    classify1=c1,
                    classify2=c2,
                    classify3=c3,
                    relative_path=rel,
                )
                self.entries.append(entry)
                self.total_files += 1
                self.total_lines += lines
                self.type_counts[file_type] += 1
                self.type_lines[file_type] += lines

        self.entries.sort(key=lambda e: e.line_count, reverse=True)

    def _summary_block(self) -> str:
        """生成 markdown 汇总表（按类型统计文件数与行数）。"""
        lines = [
            f"# {self.project_name} -- Code Statistics\n",
            f"**Total files:** {self.total_files}  |  **Total lines:** {self.total_lines}\n",
            "\n## Breakdown by Type\n",
            "| Type | Files | Lines |\n",
            "| --- | --- | --- |\n",
        ]

        # 类型按行数降序排列
        sorted_types = sorted(self.type_lines.items(), key=lambda x: -x[1])
        for t, lc in sorted_types:
            fc = self.type_counts[t]
            lines.append(f"| {t} | {fc} | {lc} |\n")

        lines.append(f"| **Total** | **{self.total_files}** | **{self.total_lines}** |\n")
        return "".join(lines)

    def print_summary(self) -> None:
        """向 stdout 打印一行紧凑的分类汇总（便于快速浏览）。"""
        grouped = sorted(self.type_lines.items(), key=lambda x: -x[1])
        parts = [f"{t}: {self.type_counts[t]} files / {lc} lines" for t, lc in grouped]
        print(f"Summary for '{self.project_name}' -- {self.total_files} files, {self.total_lines} lines")
        print("\n".join(parts))

    def print_markdown(self, filepath: Optional[Path] = None) -> str:
        """写出详细的 markdown 报告（汇总 + 逐文件表格）。"""
        md = self._summary_block()
        md += "\n## Per-File Detail\n"
        md += "| File Name | Type | Lines | C1 | C2 | C3 | Path |\n"
        md += "| --- | --- | --- | --- | --- | --- | --- |\n"
        for e in self.entries:
            md += e.to_markdown_row()
        md += f"| **Sum** | | **{self.total_lines}** | | | | |\n"

        if filepath is None:
            filepath = self.output_dir / f"{self.project_name.lower()}_code_stats.md"

        filepath.write_text(md, encoding="utf-8")
        print(f"{_C_RED}Markdown report -> {filepath}{_C_RESET}")
        return md

    def print_csv(self, filepath: Optional[Path] = None) -> None:
        """写出 CSV 报告。"""
        if filepath is None:
            filepath = self.output_dir / f"{self.project_name.lower()}_code_stats.csv"

        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["file_name", "type", "line_count", "file_classify1", "file_classify2", "file_classify3", "file_path"])
            for e in self.entries:
                writer.writerow(e.to_csv_row())
            writer.writerow(["sum", "", self.total_lines, "", "", "", ""])
        print(f"{_C_RED}CSV report      -> {filepath}{_C_RESET}")

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count lines of source code in a project tree. "
                    "Only non-blank lines are counted; excluded directories "
                    "(build/, .git/, node_modules/, ...) are pruned at any depth.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s                              # scan cwd -> ./code_stats/default/\n"
            "  %(prog)s /path/to/project             # scan project -> ./code_stats/project/\n"
            "  %(prog)s /path/to/project -o /out     # custom output dir\n"
            "  %(prog)s /path -d 2                   # classify depth 2\n"
            "  %(prog)s /path --depth 3              # classify depth 3\n"
            "  %(prog)s /path --include-empty        # keep 0-line files in reports\n"
        ),
    )
    parser.add_argument("directory", nargs="?", default=".",
                        help="Root of the source tree (default: current dir)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output directory for reports (default: ./code_stats/{project_name})")
    parser.add_argument("-d", "--depth", type=int, default=1, choices=[1, 2, 3],
                        help="Subdirectory classify depth (1-3, default: 1)")
    parser.add_argument("--include-empty", action="store_true",
                        help="Also list files that contain no non-blank lines "
                             "(default: such files are skipped)")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    input_dir = Path(args.directory).resolve()
    if not input_dir.is_dir():
        print(f"error: not a valid directory: {input_dir}", file=sys.stderr)
        sys.exit(1)

    return args

def main() -> None:
    # 先解析参数，使 --help / --version 能干净退出（不打印启动横幅）。
    args = parse_args()

    t_start = datetime.datetime.now()
    print(f"{_C_GREEN}start time: {t_start.strftime('%Y-%m-%d %H:%M:%S')}{_C_RESET}")

    input_dir = Path(args.directory).resolve()

    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        project_folder = input_dir.name if args.directory != "." else "default"
        output_dir = Path.cwd() / "code_stats" / project_folder

    output_dir.mkdir(parents=True, exist_ok=True)

    stats = CodeStatistics(
        input_dir,
        output_dir=output_dir,
        depth=args.depth,
        include_empty=args.include_empty,
    )
    stats.scan()
    stats.print_summary()
    stats.print_markdown()
    stats.print_csv()

    t_end = datetime.datetime.now()
    elapsed = t_end - t_start
    print(f"{_C_GREEN}end time:   {t_end.strftime('%Y-%m-%d %H:%M:%S')}{_C_RESET}")
    print(f"{_C_CYAN}elapsed:    {elapsed.total_seconds():.2f}s{_C_RESET}")

if __name__ == "__main__":
    main()
