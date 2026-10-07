"""Execute a sandboxed run and classify what happened.

``run_sandbox`` is deliberately boring: run the argv, watch the clock,
translate the outcome into a :class:`SandboxResult`. The subprocess runner
is injectable so every classification path is unit-testable without Docker.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
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
