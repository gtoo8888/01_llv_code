"""Tests for CountWord.py — output paths, file/line counts, exclusions."""

import csv
import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _report_path(base_dir: Path, project_name: str, ext: str) -> Path:
    """Return the report file path given the base output directory."""
    return base_dir / f"{project_name.lower()}_code_stats.{ext}"

COUNTWORD_PY = Path(__file__).resolve().parent.parent / "CountWord.py"
FIXTURES_DIR = COUNTWORD_PY.parent / "tests" / "fixtures"


def run_countword(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run CountWord.py and return the completed process."""
    cmd = ["python3", str(COUNTWORD_PY), *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


@pytest.fixture(autouse=True)
def _cleanup_code_stats():
    """Auto-clean any code_stats/ dir that leaks into fixtures during tests."""
    yield
    for d in FIXTURES_DIR.rglob("code_stats"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)


# ── Output Directory Tests ──────────────────────────────────────────────

class TestOutputDir:
    """Verify default output path logic (fix from #2)."""

    def test_with_path_uses_dir_name(self, empty_dir, tmp_path):
        """With a path given → output under code_stats/{dir_name}/."""
        os.chdir(tmp_path)
        result = run_countword(str(empty_dir), cwd=tmp_path)

        out_dir = tmp_path / "code_stats" / "empty_project"
        assert out_dir.is_dir(), f"Expected {out_dir} to exist"
        assert _report_path(out_dir, "empty_project", "md").is_file()
        assert _report_path(out_dir, "empty_project", "csv").is_file()
        assert "Markdown report" in result.stdout

    def test_project_goes_to_code_stats_project_name(self, tiny_project, tmp_path):
        """With project path → output under code_stats/{project_name}/."""
        os.chdir(tmp_path)
        result = run_countword(str(tiny_project), cwd=tmp_path)

        out_dir = tmp_path / "code_stats" / "tiny_project"
        assert out_dir.is_dir(), f"Expected {out_dir} to exist"
        assert _report_path(out_dir, "tiny_project", "md").is_file()
        assert _report_path(out_dir, "tiny_project", "csv").is_file()

    def test_custom_o_flag(self, simple_project, tmp_path):
        """-o flag overrides default output path."""
        custom = tmp_path / "my_reports"
        result = run_countword("-o", str(custom), str(simple_project), cwd=tmp_path)

        assert custom.is_dir()
        assert _report_path(custom, "simple_project", "md").is_file()
        assert _report_path(custom, "simple_project", "csv").is_file()

    def test_output_not_inside_input_dir(self, simple_project, tmp_path):
        """Default output must NOT be inside the scanned project dir."""
        os.chdir(tmp_path)
        run_countword(str(simple_project), cwd=tmp_path)

        # There should NOT be a code_stats/ folder inside the project
        assert not (simple_project / "code_stats").exists(), \
            "Output leaked into the scanned project directory"

    def test_no_args_goes_to_default(self, empty_dir, tmp_path):
        """No args given → code_stats/default/ (via '.' default in argparse)."""
        os.chdir(empty_dir)
        result = run_countword(cwd=empty_dir)

        out_dir = empty_dir / "code_stats" / "default"
        assert out_dir.is_dir(), f"Expected {out_dir} to exist"
        assert "Markdown report" in result.stdout

    def test_pwd_code_stats_not_created(self, simple_project, tmp_path):
        """Running from a temp dir should NOT litter the project's own cwd."""
        os.chdir(tmp_path)
        run_countword(str(simple_project), cwd=tmp_path)

        # No code_stats/ in the project itself
        assert not (simple_project / "code_stats").exists()


# ── File / Line Count Tests ─────────────────────────────────────────────

class TestCounts:
    """Verify correct file and line counting."""

    def test_simple_project_counts(self, simple_project, tmp_path):
        """simple_project: 6 files with known line counts."""
        os.chdir(tmp_path)
        run_countword(str(simple_project), cwd=tmp_path)
        csv_path = tmp_path / "code_stats" / "simple_project" / f"simple_project_code_stats.csv"

        rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
        # Remove trailing "sum" marker row
        rows = [r for r in rows if r["file_name"] != "sum"]

        file_types = {r["file_name"]: r["type"] for r in rows}
        assert file_types["main.c"] == "C"
        assert file_types["utils.h"] == "C/C++ Header"
        assert file_types["module.cpp"] == "C++"
        assert file_types["module.hpp"] == "C++ Header"
        assert file_types["helper.py"] == "Python"
        assert file_types["script.sh"] == "Script"

        # Verify line counts (content without blank lines)
        line_counts = {r["file_name"]: int(r["line_count"]) for r in rows}
        assert line_counts["main.c"] == 5      # 5 non-blank lines
        assert line_counts["utils.h"] == 5     # 5 non-blank lines (incl #endif)
        assert line_counts["module.cpp"] == 12  # 12 non-blank lines

    def test_tiny_project(self, tiny_project, tmp_path):
        """tiny_project: 1 file, 1 line."""
        os.chdir(tmp_path)
        run_countword(str(tiny_project), cwd=tmp_path)
        csv_path = tmp_path / "code_stats" / "tiny_project" / f"tiny_project_code_stats.csv"

        rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
        rows = [r for r in rows if r["file_name"] != "sum"]
        assert len(rows) == 1
        assert rows[0]["file_name"] == "main.py"
        assert rows[0]["line_count"] == "1"
        assert rows[0]["type"] == "Python"

    def test_summary_output(self, simple_project, tmp_path):
        """Terminal summary shows correct totals."""
        os.chdir(tmp_path)
        result = run_countword(str(simple_project), cwd=tmp_path)
        stdout = result.stdout

        assert "Summary for 'simple_project' -- 6 files" in stdout

    def test_classify_by_first_subdir(self, simple_project, tmp_path):
        """classify column shows first subdirectory, or (root) for top-level files."""
        os.chdir(tmp_path)
        run_countword(str(simple_project), cwd=tmp_path)
        csv_path = tmp_path / "code_stats" / "simple_project" / f"simple_project_code_stats.csv"

        rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
        rows = [r for r in rows if r["file_name"] != "sum"]
        for r in rows:
            # Root-level files have no directory component → classify1 is "root"
            assert r["file_classify1"] == "root", \
                f"{r['file_name']}: expected 'root', got '{r['file_classify1']}'"


# ── Exclusion Tests ─────────────────────────────────────────────────────

class TestExclusions:
    """Verify filter patterns exclude expected files/dirs."""

    def test_excluded_dir_build(self, excluded_project, tmp_path):
        """build/ directory should be excluded."""
        os.chdir(tmp_path)
        run_countword(str(excluded_project), cwd=tmp_path)
        csv_path = tmp_path / "code_stats" / "excluded_project" / f"excluded_project_code_stats.csv"

        rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
        rows = [r for r in rows if r["file_name"] != "sum"]
        filenames = {r["file_name"] for r in rows}

        assert "temp.c" not in filenames, "temp.c inside build/ should be excluded"
        assert "bench.c" not in filenames, "bench.c inside webbench-1.5/ should be excluded"
        assert "keep.c" in filenames, "keep.c in subdir/ should be included"
        assert "main.c" in filenames, "main.c at root should be included"

    def test_excluded_count(self, excluded_project, tmp_path):
        """excluded_project should only have 2 files (main.c + keep.c)."""
        os.chdir(tmp_path)
        result = run_countword(str(excluded_project), cwd=tmp_path)
        assert "2 files" in result.stdout


# ── Edge Case Tests ─────────────────────────────────────────────────────

class TestEdgeCases:
    """Handle empty dirs, zero-line files, and unusual inputs."""

    def test_empty_directory(self, empty_dir, tmp_path):
        """Empty directory → 0 files, 0 lines."""
        os.chdir(tmp_path)
        result = run_countword(str(empty_dir), cwd=tmp_path)
        assert "0 files, 0 lines" in result.stdout

    def test_invalid_directory(self, tmp_path):
        """Non-existent directory → error message + exit."""
        os.chdir(tmp_path)
        result = run_countword("/nonexistent/path", cwd=tmp_path)
        assert result.returncode == 1
        assert "not a valid directory" in result.stderr

    def test_current_dir_default(self, simple_project, tmp_path):
        """Running from inside a project dir scans it (default='.')."""
        os.chdir(simple_project)
        result = run_countword(cwd=simple_project)
        stdout = result.stdout

        assert "Summary for 'simple_project'" in stdout
        assert "6 files" in stdout

    def test_markdown_format(self, simple_project, tmp_path):
        """Generated markdown has expected header + table."""
        os.chdir(tmp_path)
        run_countword(str(simple_project), cwd=tmp_path)
        md_path = tmp_path / "code_stats" / "simple_project" / f"simple_project_code_stats.md"
        md = md_path.read_text(encoding="utf-8")

        assert "# simple_project -- Code Statistics" in md
        assert "## Breakdown by Type" in md
        assert "## Per-File Detail" in md
        assert "| File Name | Type | Lines | C1 | C2 | C3 | Path |" in md

    def test_csv_format(self, simple_project, tmp_path):
        """Generated CSV has expected headers."""
        os.chdir(tmp_path)
        run_countword(str(simple_project), cwd=tmp_path)
        csv_path = tmp_path / "code_stats" / "simple_project" / f"simple_project_code_stats.csv"
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert headers == ["file_name", "type", "line_count", "file_classify1", "file_classify2", "file_classify3", "file_path"]

    def test_subdir_classify(self, excluded_project, tmp_path):
        """Files in subdirectories get correct classify value."""
        os.chdir(tmp_path)
        run_countword(str(excluded_project), cwd=tmp_path)
        csv_path = tmp_path / "code_stats" / "excluded_project" / f"excluded_project_code_stats.csv"
        rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))

        classify_map = {r["file_name"]: r["file_classify1"] for r in rows if r["file_name"] != "sum"}
        assert classify_map["keep.c"] == "subdir"
        assert classify_map["main.c"] == "root"  # root-level → "root"


# ── Clean Run Tests ─────────────────────────────────────────────────────

class TestCleanRun:
    """Non-functional checks: no stderr, no unexpected output."""

    def test_no_stderr_on_valid_input(self, simple_project, tmp_path):
        """Valid input produces no stderr."""
        os.chdir(tmp_path)
        result = run_countword(str(simple_project), cwd=tmp_path)
        assert result.stderr == "" or "unreadable file" not in result.stderr

    def test_exit_code_zero(self, simple_project, tmp_path):
        """Successful run returns exit code 0."""
        os.chdir(tmp_path)
        result = run_countword(str(simple_project), cwd=tmp_path)
        assert result.returncode == 0


# ── Depth Tests ────────────────────────────────────────────────────────────

class TestDepth:
    """Verify --depth flag controls classify columns."""

    def test_depth_1_empty_columns(self, tmp_path):
        "depth=1: classify1 filled, classify2/3 empty"
        proj = tmp_path / "a" / "b" / "c"
        proj.mkdir(parents=True)
        (proj / "test.c").write_text("int x;\n")
        os.chdir(tmp_path)
        run_countword(str(tmp_path / "a"), "--depth", "1", cwd=tmp_path)
        csv_path = tmp_path / "code_stats" / "a" / f"a_code_stats.csv"
        rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
        r = [x for x in rows if x["file_name"] != "sum"][0]
        assert r["file_classify1"] == "b"
        assert r["file_classify2"] == ""
        assert r["file_classify3"] == ""

    def test_depth_2_second_filled(self, tmp_path):
        "depth=2: classify1/2 filled, classify3 empty"
        proj = tmp_path / "x" / "y" / "z"
        proj.mkdir(parents=True)
        (proj / "test.c").write_text("int x;\n")
        os.chdir(tmp_path)
        run_countword(str(tmp_path / "x"), "--depth", "2", cwd=tmp_path)
        csv_path = tmp_path / "code_stats" / "x" / f"x_code_stats.csv"
        rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
        r = [x for x in rows if x["file_name"] != "sum"][0]
        assert r["file_classify1"] == "y"
        assert r["file_classify2"] == "y/z"
        assert r["file_classify3"] == ""

    def test_depth_3_three_levels(self, tmp_path):
        "depth=3: classify1/2/3 filled for 3+ level paths"
        proj = tmp_path / "src" / "Player" / "VideoPlay"
        proj.mkdir(parents=True)
        (proj / "VoiceDecode.cpp").write_text("void decode() {}\n")
        os.chdir(tmp_path)
        # Scan parent of src/ so relative path is src/Player/VideoPlay/VoiceDecode.cpp
        run_countword(str(tmp_path), "--depth", "3", cwd=tmp_path)
        csv_path = tmp_path / "code_stats" / tmp_path.name / f"{tmp_path.name.lower()}_code_stats.csv"
        rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
        r = [x for x in rows if x["file_name"] != "sum"][0]
        assert r["file_classify1"] == "src"
        assert r["file_classify2"] == "src/Player"
        assert r["file_classify3"] == "src/Player/VideoPlay"

    def test_depth_default_is_1(self, tmp_path):
        "No --depth flag → defaults to 1"
        proj = tmp_path / "sub" / "deep"
        proj.mkdir(parents=True)
        (proj / "test.c").write_text("int x;\n")
        os.chdir(tmp_path)
        run_countword(str(tmp_path / "sub"), cwd=tmp_path)
        csv_path = tmp_path / "code_stats" / "sub" / f"sub_code_stats.csv"
        rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
        r = [x for x in rows if x["file_name"] != "sum"][0]
        assert r["file_classify1"] == "deep"
        assert r["file_classify2"] == ""
        assert r["file_classify3"] == ""

    def test_invalid_depth_rejected(self, tmp_path):
        "Invalid depth value → error exit"
        os.chdir(tmp_path)
        result = run_countword("--depth", "4", str(tmp_path), cwd=tmp_path)
        assert result.returncode != 0
