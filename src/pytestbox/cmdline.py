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


def build_docker_run(
    *,
    image: str,
    workspace: str,
    command: list[str],
    container_name: str,
    memory: str = "512m",
    cpus: float = 1.0,
) -> list[str]:
    """Assemble the full ``docker run`` argv for one sandboxed execution."""
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
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
        "/tmp:rw,noexec,nosuid,size=64m",
        "-v",
        f"{workspace}:/workspace:ro",
        "-w",
        "/workspace",
        image,
        *command,
    ]
