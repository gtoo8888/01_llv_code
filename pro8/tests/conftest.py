"""Shared fixtures for CountWord tests."""

import subprocess
import shutil
from pathlib import Path
from typing import Iterator

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COUNTWORD_PY = PROJECT_ROOT / "CountWord.py"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture
def simple_project() -> Path:
    return FIXTURES_DIR / "simple_project"


@pytest.fixture
def excluded_project() -> Path:
    return FIXTURES_DIR / "excluded_project"


@pytest.fixture
def tiny_project() -> Path:
    return FIXTURES_DIR / "tiny_project"


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    d = tmp_path / "empty_project"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def run_dir(tmp_path: Path) -> Iterator[Path]:
    """Provide a clean temp directory to run CountWord from."""
    cwd = Path.cwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(cwd)


def run_countword(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run CountWord.py and return the completed process."""
    cmd = ["python3", str(COUNTWORD_PY), *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


import os
