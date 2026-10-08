"""Shared fixtures: a tiny sample project for CLI wiring tests."""

from pathlib import Path

import pytest


@pytest.fixture
def make_project(tmp_path: Path) -> Path:
    """A minimal project with one green test suite."""
    root = tmp_path / "project"
    (root / "tests").mkdir(parents=True)
    (root / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    assert 1 + 1 == 2\n",
        encoding="utf-8",
    )
    return root
