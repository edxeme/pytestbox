"""Integration tests — real Docker, real containers.

Skipped automatically when Docker is unavailable; they run in CI where
Docker is part of the runner.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import pytestbox.cli as cli
from pytestbox.runner import build_image

pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None, reason="docker not available"
)

SANDBOX_IMAGE = "pytestbox:it-py312"


@pytest.fixture(scope="module")
def sandbox_image():
    build_image(tag=SANDBOX_IMAGE, python_tag="3.12")
    return SANDBOX_IMAGE


def _green_project(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    assert 1 + 1 == 2\n"
    )
    return tmp_path


def test_green_suite_runs_passed_in_sandbox(tmp_path, sandbox_image, capsys):
    root = _green_project(tmp_path)

    rc = cli.main(["run", str(root), "--image", sandbox_image, "--json"])

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "passed"
    assert data["summary"] == {"passed": 1}


def test_red_suite_runs_failed_in_sandbox(tmp_path, sandbox_image, capsys):
    root = _green_project(tmp_path)
    (root / "tests" / "test_bad.py").write_text(
        "def test_bad():\n    assert 1 + 1 == 3\n"
    )

    rc = cli.main(["run", str(root), "--image", sandbox_image, "--json"])

    assert rc == 1
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "failed"
    assert data["summary"]["failed"] == 1


def test_hung_suite_times_out_and_leaves_no_orphan(tmp_path, sandbox_image, capsys):
    root = _green_project(tmp_path)
    (root / "tests" / "test_hang.py").write_text(
        "import time\n\n\ndef test_hangs():\n    time.sleep(600)\n"
    )

    rc = cli.main(
        ["run", str(root), "--image", sandbox_image, "--json", "--timeout", "5"]
    )

    assert rc == 2
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "timed_out"

    listing = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=pytestbox-", "--format", "{{.ID}}"],
        capture_output=True,
        text=True,
    )
    assert listing.stdout.strip() == ""  # no orphaned containers
