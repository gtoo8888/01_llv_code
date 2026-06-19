# -*- coding: utf-8 -*-
"""
Code Statistics Tool -- count lines, classify by extension, summarize by type.

Compatible with Python 3.8+ (uses dataclasses from stdlib, typing module generics).
Python 3.8 is the minimum supported version; no external dependencies required.
"""

import argparse
import csv
import datetime
import fnmatch
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

# Default output subfolder name (used only when CodeStatistics is called directly)
_DEFAULT_OUTPUT_DIR = "code_stats"

# ANSI color codes for terminal output
_C_GREEN = "\033[92m"
_C_CYAN = "\033[96m"
_C_YELLOW = "\033[93m"
_C_RED = "\033[91m"
_C_RESET = "\033[0m"

# File patterns to skip (glob-style wildcards, matched against basename)
_FILTER_LANG_BUILD: List[str] = [
    "*.pyc", "*.pyo",
    "*.o", "*.obj",
    "*.a", "*.so", "*.dll", "*.lib", "*.exe",
    "*.out",
]

_FILTER_IDE_OS: List[str] = [
    ".DS_Store", "Thumbs.db",  # OS metadata
    "*~", "*.swp", "*.swo",   # backup / vim swap
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


# Directory patterns to skip (glob-style, matched against relative path)
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

# Extension → type mapping (the pattern is used with glob.iglob)
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
    # uncomment below if desired
    # "*.md":      "Markdown",
    # "CMake*":    "Build",
    # "Make*":     "Build",
    # ".gitlab-ci.yml": "CI",
}

@dataclass
class CodeEntry:
    """Statistics for one matched source file."""
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
    ):
        self.input_dir: Path = input_dir.resolve()
        self.output_dir: Path = (output_dir or input_dir / _DEFAULT_OUTPUT_DIR).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.depth: int = depth
        self.filter_files: List[str] = filter_files or _DEFAULT_FILTER_FILES
        self.filter_dirs: List[str] = filter_dirs or _DEFAULT_FILTER_DIRS
        self.extensions: Dict[str, str] = extensions or dict(_DEFAULT_EXTENSIONS)

        self.project_name: str = self.input_dir.name
        self.entries: List[CodeEntry] = []

        self.total_files: int = 0
        self.total_lines: int = 0
        self.type_counts: Dict[str, int] = defaultdict(int)       # file count per type
        self.type_lines: Dict[str, int] = defaultdict(int)        # line count per type

    @staticmethod
    def _count_lines(file_path: Path) -> int:
        try:
            with open(file_path, "rb") as f:
                return sum(1 for line in f if line.strip())
        except (OSError, PermissionError) as exc:
            print(f"  [skip] unreadable file: {file_path} -- {exc}", file=sys.stderr)
            return 0

    @staticmethod
    def _classify_levels(rel_path: str, depth: int = 1) -> tuple[str, str, str]:
        """Extract up to 3 cumulative directory levels; missing levels fall back to previous."""
        parts = Path(rel_path).parent.parts    # drop filename, keep dirs only
        # Root-level files: parent is "." → parts = () → set to ("root",)
        if not parts:
            parts = ("root",)
        c1 = parts[0] if len(parts) > 0 else ""

        if len(parts) > 1:
            c2 = "/".join(parts[:2])
        else:
            c2 = c1  # fallback to previous level

        if len(parts) > 2:
            c3 = "/".join(parts[:3])
        else:
            c3 = c2  # fallback to previous level

        if depth < 2:
            c2 = ""
        if depth < 3:
            c3 = ""
        return c1, c2, c3

    def _is_excluded_file(self, name: str) -> bool:
        return any(fnmatch.fnmatch(name, pat) for pat in self.filter_files)

    def _is_excluded_dir(self, rel_path: str) -> bool:
        return any(fnmatch.fnmatch(rel_path, pat) for pat in self.filter_dirs)

    def scan(self) -> None:
        """Walk the input directory and collect statistics."""
        self.entries.clear()
        self.total_files = 0
        self.total_lines = 0
        self.type_counts.clear()
        self.type_lines.clear()

        for pattern, file_type in self.extensions.items():
            for file_path in sorted(self.input_dir.rglob(pattern)):
                file_name = file_path.name

                # skip excluded file name patterns
                if self._is_excluded_file(file_name):
                    continue

                # skip excluded directory patterns (check every ancestor)
                rel = file_path.relative_to(self.input_dir).as_posix()
                if any(
                    self._is_excluded_dir(part)
                    for part in Path(rel).parents
                ):
                    continue

                lines = self._count_lines(file_path)
                if lines == 0:
                    continue

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
        """Produce a markdown summary table (file count + line count by type)."""
        lines = [
            f"# {self.project_name} -- Code Statistics\n",
            f"**Total files:** {self.total_files}  |  **Total lines:** {self.total_lines}\n",
            "\n## Breakdown by Type\n",
            "| Type | Files | Lines |\n",
            "| --- | --- | --- |\n",
        ]

        # sort types descending by lines
        sorted_types = sorted(self.type_lines.items(), key=lambda x: -x[1])
        for t, lc in sorted_types:
            fc = self.type_counts[t]
            lines.append(f"| {t} | {fc} | {lc} |\n")

        lines.append(f"| **Total** | **{self.total_files}** | **{self.total_lines}** |\n")
        return "".join(lines)

    def print_summary(self) -> None:
        """Print a compact one-line breakdown to stdout (for quick glance)."""
        grouped = sorted(self.type_lines.items(), key=lambda x: -x[1])
        parts = [f"{t}: {self.type_counts[t]} files / {lc} lines" for t, lc in grouped]
        print(f"Summary for '{self.project_name}' -- {self.total_files} files, {self.total_lines} lines")
        print("\n".join(parts))

    def print_markdown(self, filepath: Optional[Path] = None) -> str:
        """Write detailed markdown report (summary + per-file table)."""
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
        """Write CSV report."""
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
        description="Count lines of source code in a project tree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s                              # scan cwd -> ./code_stats/default/\n"
            "  %(prog)s /path/to/project             # scan project -> ./code_stats/project/\n"
            "  %(prog)s /path/to/project -o /out     # custom output dir\n"
            "  %(prog)s /path -d 2                   # classify depth 2\n"
            "  %(prog)s /path --depth 3              # classify depth 3\n"
        ),
    )
    parser.add_argument("directory", nargs="?", default=".",
                        help="Root of the source tree (default: current dir)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output directory for reports (default: ./code_stats/{project_name})")
    parser.add_argument("-d", "--depth", type=int, default=1, choices=[1, 2, 3],
                        help="Subdirectory classify depth (1-3, default: 1)")
    args = parser.parse_args(argv)

    input_dir = Path(args.directory).resolve()
    if not input_dir.is_dir():
        print(f"error: not a valid directory: {input_dir}", file=sys.stderr)
        sys.exit(1)

    return args

def main() -> None:
    t_start = datetime.datetime.now()
    print(f"{_C_GREEN}start time: {t_start.strftime('%Y-%m-%d %H:%M:%S')}{_C_RESET}")

    args = parse_args()

    input_dir = Path(args.directory).resolve()

    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        project_folder = input_dir.name if args.directory != "." else "default"
        output_dir = Path.cwd() / "code_stats" / project_folder

    output_dir.mkdir(parents=True, exist_ok=True)

    stats = CodeStatistics(input_dir, output_dir=output_dir, depth=args.depth)
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
