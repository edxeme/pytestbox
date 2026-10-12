"""Build the ``docker run`` argv for a locked-down sandbox.

Pure argument construction — no Docker calls here, so the security
posture of every sandbox is visible in one place and unit-testable:

- ``--network none``: suites never touch the network.
- ``--read-only`` root filesystem; the workspace mounts ``:ro``; the only
  writable host path is... none. A ``/tmp`` tmpfs covers pytest tmp dirs.
- ``--memory`` / ``--cpus`` / ``--pids-limit`` cap runaway resources
  (fork bombs included).
- ``--cap-drop ALL`` + ``no-new-privileges`` strip escalation paths.
- The container gets a stable ``--name`` so the runner can ``docker kill``
  it when the host-side timeout fires.
"""

from __future__ import annotations

import os

#: The command sandboxed suites run by default: pytest with no cache writes
#: (the root filesystem is read-only) and quiet output.
DEFAULT_PYTEST_COMMAND = [
    "python",
    "-m",
    "pytest",
    "-p",
    "no:cacheprovider",
    "-q",
]


def host_user() -> str | None:
    """The invoking user as ``uid:gid`` — ``None`` where POSIX ids don't exist."""
    try:
        return f"{os.getuid()}:{os.getgid()}"
    except AttributeError:  # Windows: no uid/gid concept
        return None


def build_docker_run(
    *,
    image: str,
    workspace: str,
    command: list[str],
    container_name: str,
    memory: str = "512m",
    cpus: float = 1.0,
    user: str | None = None,
) -> list[str]:
    """Assemble the full ``docker run`` argv for one sandboxed execution."""
    argv = [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
    ]
    if user is not None:
        # Run as the invoking user: least privilege, and file permissions on
        # the mounted workspace resolve exactly as they do on the host.
        # (root with --cap-drop ALL loses DAC_OVERRIDE and cannot even stat
        # into pytest's permission-hardened tmp_path directories.)
        argv += ["--user", user]
    argv += [
        "--network",
        "none",
        "--memory",
        memory,
        "--cpus",
        str(cpus),
        "--pids-limit",
        "128",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m,mode=1777",
        "-v",
        f"{workspace}:/workspace:ro",
        "-w",
        "/workspace",
        image,
        *command,
    ]
    return argv
