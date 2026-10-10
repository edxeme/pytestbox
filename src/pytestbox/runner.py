"""Execute sandboxed runs and build the sandbox image.

``run_sandbox`` is deliberately boring: run the argv, watch the clock,
translate the outcome into a :class:`SandboxResult`. ``build_image``
prepares the default sandbox image with pytest preinstalled, so sandboxes
themselves can run with ``--network none``. Both subprocess runners are
injectable so every path is unit-testable without Docker.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pytestbox.parser import parse_summary

#: pytest exit codes carry meaning: 0 = all green, 1 = tests failed.
#: Anything else (2 = interrupted, 3 = internal error, 4 = usage, 5 = no
#: tests collected) is an *error* of the run, not a test failure.
_EXIT_STATUS = {0: "passed", 1: "failed"}


@dataclass
class SandboxResult:
    """What one sandboxed execution did, structured for humans and CI."""

    status: str  # passed | failed | timed_out | error
    exit_code: int | None
    duration_seconds: float
    output: str = ""
    summary: dict[str, int] | None = field(default=None)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "exit_code": self.exit_code,
            "duration_seconds": round(self.duration_seconds, 3),
            "summary": self.summary,
            "output": self.output,
        }


def run_sandbox(
    argv: list[str],
    *,
    timeout_seconds: int = 300,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> SandboxResult:
    """Run *argv* under a hard timeout and classify the outcome."""
    started = time.monotonic()
    try:
        proc = runner(argv, capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return _result("timed_out", None, started)
    except OSError as exc:
        return _result("error", None, started, output=str(exc))

    output = f"{proc.stdout or ''}{proc.stderr or ''}"
    status = _EXIT_STATUS.get(proc.returncode, "error")
    return _result(status, proc.returncode, started, output=output)


def _result(
    status: str,
    exit_code: int | None,
    started: float,
    output: str = "",
) -> SandboxResult:
    return SandboxResult(
        status=status,
        exit_code=exit_code,
        duration_seconds=time.monotonic() - started,
        output=output,
        summary=parse_summary(output),
    )


#: The sandbox image: python slim plus pytest, nothing else. Sandboxes run
#: with ``--network none``, so the dependencies must already be inside.
SANDBOX_DOCKERFILE = '''FROM python:{python_tag}-slim
RUN pip install --no-cache-dir "pytest>=8,<10"
'''


class ImageBuildError(RuntimeError):
    """Raised when the sandbox image fails to build."""


def build_image(
    tag: str = "pytestbox:py312",
    python_tag: str = "3.12",
    *,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> str:
    """Build the default sandbox image and return its tag."""
    with tempfile.TemporaryDirectory() as build_dir:
        dockerfile = Path(build_dir, "Dockerfile")
        dockerfile.write_text(SANDBOX_DOCKERFILE.format(python_tag=python_tag))
        proc = runner(
            ["docker", "build", "-t", tag, build_dir],
            capture_output=True,
            text=True,
        )

    if proc.returncode != 0:
        raise ImageBuildError(proc.stderr or proc.stdout or "docker build failed")
    return tag
