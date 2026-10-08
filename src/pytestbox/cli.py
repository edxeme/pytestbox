"""Command-line interface for pytestbox."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pytestbox.cmdline import DEFAULT_PYTEST_COMMAND, build_docker_run
from pytestbox.runner import run_sandbox

#: Exit codes: chosen so pytestbox drops into CI pipelines cleanly —
#: failed tests must fail the pipeline; a sandbox malfunction must fail it
#: louder.
_EXIT_CODES = {"passed": 0, "failed": 1, "timed_out": 2, "error": 3}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pytestbox",
        description=(
            "Run untrusted pytest suites in locked-down Docker sandboxes: "
            "no network, hard resource caps, host-enforced timeout."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="run a test suite inside the sandbox")
    p_run.add_argument("path", help="project root to mount read-only at /workspace")
    p_run.add_argument("--image", default="pytestbox:py312", help="sandbox image")
    p_run.add_argument(
        "--timeout", type=int, default=300, help="hard timeout in seconds"
    )
    p_run.add_argument("--memory", default="512m", help="container memory cap")
    p_run.add_argument("--cpus", type=float, default=1.0, help="container CPU cap")
    p_run.add_argument("--json", action="store_true", help="emit the result as JSON")
    # The sandboxed command is everything argparse cannot attribute (after
    # `--`), captured via parse_known_args in main().

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    # parse_known_args: whatever the sandbox should run arrives as the
    # unrecognized remainder (pytestbox has no reason to know pytest flags).
    args, extra = parser.parse_known_args(argv)

    root = Path(args.path).resolve()
    if not root.is_dir():
        parser.exit(1, f"pytestbox: not a directory: {args.path}\n")

    command = list(extra)
    if command and command[0] == "--":
        command = command[1:]
    command = command or DEFAULT_PYTEST_COMMAND

    sandbox_argv = build_docker_run(
        image=args.image,
        workspace=str(root),
        command=command,
        container_name="pytestbox-cli",
    )
    result = run_sandbox(sandbox_argv, timeout_seconds=args.timeout)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        if result.output:
            print(result.output, end="" if result.output.endswith("\n") else "\n")
        print(
            f"pytestbox: {result.status} · exit={result.exit_code} · "
            f"{result.duration_seconds:.1f}s",
            file=sys.stderr,
        )
    return _EXIT_CODES[result.status]
