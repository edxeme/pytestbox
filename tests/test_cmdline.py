"""Tests for the docker run argv builder."""

import re

from pytestbox.cmdline import DEFAULT_PYTEST_COMMAND, build_docker_run, host_user


def test_builds_full_locked_down_argv():
    argv = build_docker_run(
        image="pytestbox:py312",
        workspace="/tmp/proj",
        command=["python", "-m", "pytest", "-q"],
        container_name="pytestbox-abc123",
        user="1001:1001",
    )

    assert argv == [
        "docker",
        "run",
        "--rm",
        "--name",
        "pytestbox-abc123",
        "--user",
        "1001:1001",
        "--network",
        "none",
        "--memory",
        "512m",
        "--cpus",
        "1.0",
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
        "/tmp/proj:/workspace:ro",
        "-w",
        "/workspace",
        "pytestbox:py312",
        "python",
        "-m",
        "pytest",
        "-q",
    ]


def test_user_flag_is_omitted_when_none():
    argv = build_docker_run(
        image="img",
        workspace="/w",
        command=["true"],
        container_name="pytestbox-x",
    )

    assert "--user" not in argv


def test_host_user_looks_like_uid_gid():
    if host_user() is not None:  # None on Windows, absent test there
        assert re.fullmatch(r"\d+:\d+", host_user())


def test_workspace_is_mounted_read_only():
    argv = build_docker_run(
        image="img",
        workspace="/host/path",
        command=["true"],
        container_name="pytestbox-x",
    )

    assert "/host/path:/workspace:ro" in argv
    assert "--read-only" in argv


def test_network_is_disabled():
    argv = build_docker_run(
        image="img",
        workspace="/w",
        command=["true"],
        container_name="pytestbox-x",
    )

    assert argv[argv.index("--network") + 1] == "none"


def test_resource_limits_are_configurable():
    argv = build_docker_run(
        image="img",
        workspace="/w",
        command=["true"],
        container_name="pytestbox-x",
        memory="256m",
        cpus=0.5,
    )

    assert argv[argv.index("--memory") + 1] == "256m"
    assert argv[argv.index("--cpus") + 1] == "0.5"


def test_default_command_disables_cache_writes():
    assert "-p" in DEFAULT_PYTEST_COMMAND
    assert "no:cacheprovider" in DEFAULT_PYTEST_COMMAND
