"""CLI tests: wiring, exit codes and JSON output (Docker-free via fakes)."""

import json

import pytest

import pytestbox.cli as cli
from pytestbox.runner import SandboxResult


@pytest.fixture
def canned_result(monkeypatch):
    """Replace run_sandbox with a recorder returning a fixed result."""

    def install(result: SandboxResult):
        seen: dict = {}

        def fake_run(argv, **kwargs):
            seen["argv"] = argv
            seen["kwargs"] = kwargs
            return result

        monkeypatch.setattr(cli, "run_sandbox", fake_run)
        return seen

    return install


def test_run_default_command_is_quiet_pytest(make_project, canned_result, capsys):
    seen = canned_result(
        SandboxResult(status="passed", exit_code=0, duration_seconds=1.0)
    )

    assert cli.main(["run", str(make_project)]) == 0
    assert seen["argv"][-6:] == [
        "python",
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "-q",
    ]
    assert "--json" not in seen["argv"]


def test_run_after_double_dash_overrides_command(make_project, canned_result):
    seen = canned_result(
        SandboxResult(status="passed", exit_code=0, duration_seconds=1.0)
    )

    cli.main(["run", str(make_project), "--", "pytest", "-v", "tests/unit"])

    assert seen["argv"][-3:] == ["pytest", "-v", "tests/unit"]


def test_json_flag_before_or_after_path(make_project, canned_result, capsys):
    canned_result(SandboxResult(status="passed", exit_code=0, duration_seconds=1.0))

    assert cli.main(["run", str(make_project), "--json"]) == 0
    json.loads(capsys.readouterr().out)  # --json was not swallowed

    assert cli.main(["run", "--json", str(make_project)]) == 0
    json.loads(capsys.readouterr().out)


def test_json_output_and_exit_codes(make_project, canned_result, capsys):
    cases = [
        (SandboxResult("passed", 0, 1.0, summary={"passed": 2}), 0),
        (SandboxResult("failed", 1, 1.0, summary={"failed": 2}), 1),
        (SandboxResult("timed_out", None, 5.0), 2),
        (SandboxResult("error", None, 0.1, output="boom"), 3),
    ]
    for result, expected in cases:
        canned_result(result)
        rc = cli.main(["run", str(make_project), "--json"])
        assert rc == expected

        data = json.loads(capsys.readouterr().out)
        assert data["status"] == result.status


def test_text_mode_prints_output_and_status_line(make_project, canned_result, capsys):
    canned_result(
        SandboxResult(
            status="passed",
            exit_code=0,
            duration_seconds=2.5,
            output="1 passed in 0.02s\n",
            summary={"passed": 1},
        )
    )

    rc = cli.main(["run", str(make_project)])

    captured = capsys.readouterr()
    assert rc == 0
    assert "1 passed in 0.02s" in captured.out
    assert "passed · exit=0 · 2.5s" in captured.err


def test_build_image_success_prints_tag(monkeypatch, capsys):
    captured: dict = {}

    def fake_build(tag, python_tag, **kw):
        captured["tag"] = tag
        return tag

    monkeypatch.setattr(cli, "build_image", fake_build)

    assert cli.main(["build-image", "--python", "3.13"]) == 0

    assert captured["tag"] == "pytestbox:py313"  # dots stripped — run's default
    assert "image ready: pytestbox:py313" in capsys.readouterr().out


def test_build_image_failure_exits_three(monkeypatch, capsys):
    def boom(**kwargs):
        raise cli.ImageBuildError("network down during build")

    monkeypatch.setattr(cli, "build_image", boom)

    assert cli.main(["build-image"]) == 3
    assert "network down during build" in capsys.readouterr().err


def test_missing_path_fails(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["run", "/nonexistent/pytestbox-path"])

    assert excinfo.value.code == 1
    assert "not a directory" in capsys.readouterr().err
