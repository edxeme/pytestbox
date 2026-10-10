"""Runner classification tests with an injected fake runner."""

import subprocess

import pytest

from pytestbox.runner import (
    ImageBuildError,
    SandboxResult,
    build_image,
    run_sandbox,
)


class FakeRunner:
    """Returns a canned CompletedProcess, or raises a canned exception."""

    def __init__(self, returncode=0, stdout="", stderr="", raises=None):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.raises = raises
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        if self.raises is not None:
            raise self.raises
        return subprocess.CompletedProcess(
            argv, self.returncode, stdout=self.stdout, stderr=self.stderr
        )


def test_green_suite_is_passed_and_parsed():
    fake = FakeRunner(returncode=0, stdout="test_ok.py .\n1 passed in 0.02s\n")

    result = run_sandbox(["docker", "run", "x"], runner=fake)

    assert result.status == "passed"
    assert result.exit_code == 0
    assert result.summary == {"passed": 1}
    assert result.duration_seconds >= 0


def test_failing_suite_is_failed_with_counts():
    fake = FakeRunner(returncode=1, stdout="1 failed, 2 passed in 0.10s\n")

    result = run_sandbox(["docker", "run", "x"], runner=fake)

    assert result.status == "failed"
    assert result.exit_code == 1
    assert result.summary == {"failed": 1, "passed": 2}


def test_nonzero_unexpected_exit_code_is_error():
    fake = FakeRunner(returncode=4, stdout="usage: pytest\n")  # usage error

    result = run_sandbox(["docker", "run", "x"], runner=fake)

    assert result.status == "error"
    assert result.exit_code == 4
    assert result.summary is None


def test_timeout_is_reported_as_timed_out():
    fake = FakeRunner(
        raises=subprocess.TimeoutExpired(cmd=["docker"], timeout=5)
    )

    result = run_sandbox(["docker", "run", "x"], runner=fake, timeout_seconds=5)

    assert result.status == "timed_out"
    assert result.exit_code is None
    assert result.summary is None


def test_docker_missing_is_error_not_crash():
    fake = FakeRunner(raises=OSError("docker: command not found"))

    result = run_sandbox(["docker", "run", "x"], runner=fake)

    assert result.status == "error"
    assert result.exit_code is None
    assert "docker" in result.output


def test_stderr_is_captured_into_output():
    fake = FakeRunner(returncode=1, stderr="E   AssertionError\n")

    result = run_sandbox(["docker", "run", "x"], runner=fake)

    assert "AssertionError" in result.output


def test_timeout_kills_the_named_container():
    killed: list[str] = []
    fake = FakeRunner(raises=subprocess.TimeoutExpired(cmd=["docker"], timeout=5))

    argv = [
        "docker", "run", "--name", "pytestbox-abc123", "img", "python",
    ]
    result = run_sandbox(
        argv,
        timeout_seconds=5,
        runner=fake,
        killer=lambda name: killed.append(name),
    )

    assert result.status == "timed_out"
    assert killed == ["pytestbox-abc123"]


def test_default_killer_never_raises_when_docker_is_missing():
    from pytestbox.runner import _docker_kill

    _docker_kill("pytestbox-nothing")  # must not raise


def test_build_image_returns_tag_on_success():
    fake = FakeRunner(returncode=0)

    tag = build_image(tag="pytestbox:py312", python_tag="3.12", runner=fake)

    assert tag == "pytestbox:py312"
    argv = fake.calls[0]
    assert argv[:3] == ["docker", "build", "-t"]
    assert "pytestbox:py312" in argv


def test_build_image_writes_dockerfile_with_python_tag():
    captured = {}

    def spy(argv, **kwargs):
        captured["dockerfile"] = (
            open(argv[-1] + "/Dockerfile").read()
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    build_image(tag="t", python_tag="3.13", runner=spy)

    assert "FROM python:3.13-slim" in captured["dockerfile"]
    assert "pytest" in captured["dockerfile"]


def test_build_image_failure_raises_image_build_error():
    fake = FakeRunner(returncode=1, stderr="build failed: boom")

    with pytest.raises(ImageBuildError, match="boom"):
        build_image(runner=fake)


def test_to_dict_is_json_shaped():
    result = SandboxResult(
        status="passed", exit_code=0, duration_seconds=1.23456, summary={"passed": 3}
    )

    data = result.to_dict()

    assert data["status"] == "passed"
    assert data["duration_seconds"] == 1.235  # rounded for stable JSON
    assert data["summary"] == {"passed": 3}
