"""Command-line interface for pytestbox."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from pytestbox.cmdline import DEFAULT_PYTEST_COMMAND, build_docker_run
from pytestbox.runner import ImageBuildError, build_image, run_sandbox

#: Exit codes: chosen so pytestbox drops into CI pipelines cleanly —
#: failed tests must fail the pipeline; a sandbox malfunction must fail it
#: louder.
_EXIT_CODES = {"passed": 0, "failed": 1, "timed_out": 2, "error": 3}


def sandbox_name() -> str:
    """Unique container name so host-side cleanup can kill by name."""
    return f"pytestbox-{uuid.uuid4().hex[:12]}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pytestbox",
        description=(
            "Run untrusted pytest suites in locked-down Docker sandboxes: "
            "no network, hard resource caps, host-enforced timeout."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser(
        "build-image",
        help="build the default sandbox image (pytest preinstalled)",
    )
    p_build.add_argument(
        "--python", default="3.12", help="python tag for the base image"
    )
    p_build.add_argument(
        "--tag", default=None, help="image tag (default: pytestbox:py<TAG>)"
    )

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

    if args.command == "build-image":
        # pytestbox:py3.12 and pytestbox:py312 must be the same tag or the
        # run default can never find the image — docker tags conventionally
        # avoid dots, so strip them.
        tag = args.tag or f"pytestbox:py{args.python.replace('.', '')}"
        try:
            built = build_image(tag=tag, python_tag=args.python)
        except ImageBuildError as exc:
            print(f"pytestbox: image build failed:\n{exc}", file=sys.stderr)
            return 3
        print(f"image ready: {built}")
        return 0

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
        container_name=sandbox_name(),
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
