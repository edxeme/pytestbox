# pytestbox

[![CI](https://github.com/edxeme/pytestbox/actions/workflows/ci.yml/badge.svg)](https://github.com/edxeme/pytestbox/actions/workflows/ci.yml)
[![PyPI — python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/pytestbox/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-success)](#how-it-works)

Run untrusted pytest suites in locked-down Docker sandboxes — no network,
hard memory/CPU limits, host-enforced timeouts, structured results.

```sh
$ pytestbox run sample --json
{
  "status": "passed",
  "exit_code": 0,
  "duration_seconds": 0.94,
  "summary": {
    "passed": 2
  },
  "output": "..                       [100%]\n2 passed in 0.01s\n"
}
```

## Why

Running a test suite you do not fully trust — a contributor's PR, a downloaded
project, an agent's patch — on your laptop or CI runner means running
*everything that suite does*. pytestbox wraps the run in a container that
cannot: touch the network, write to the filesystem outside a 64 MB tmpfs,
fork-bomb the host, or outlive its timeout. The result comes back structured,
so pipelines and tooling can consume it without scraping text.

## Install

```sh
pipx install pytestbox        # or: pip install pytestbox
```

Requires Python 3.11+ and a running Docker daemon.

## Usage

**Prepare the sandbox image once** — python slim plus pytest, nothing else:

```sh
$ pytestbox build-image
image ready: pytestbox:py312
```

**Run a suite** — the project mounts read-only at `/workspace`:

```sh
pytestbox run /path/to/project
pytestbox run /path/to/project --timeout 60 --memory 256m --cpus 0.5
pytestbox run /path/to/project -- pytest -v tests/unit   # custom command
```

**Consume results** — `--json` on any run; exit codes are CI-ready:

| exit | meaning |
| :--- | :--- |
| `0` | suite passed |
| `1` | tests failed (real failures, not a sandbox problem) |
| `2` | timed out — killed and reported |
| `3` | sandbox malfunction (missing image, docker daemon down, …) |

## What the sandbox enforces

- `--network none` — suites never touch the network
- `--read-only` root filesystem, workspace mounted `:ro`, `/tmp` as a
  64 MB `noexec` tmpfs — pytest tmp dirs work, nothing else persists
- `--memory` / `--cpus` / `--pids-limit 128` — runaway memory, CPU and
  fork bombs are capped
- `--cap-drop ALL` + `no-new-privileges` — no privilege escalation paths
- Host-side hard timeout — on expiry the container is killed **by name**;
  the docker client dying does not leave an orphan behind (regression-tested)

Suites that write into their own project directory will fail by design —
point them at `tmp_path`/`/tmp` instead.

## How it works

Three small pieces, all stdlib:

- `cmdline.py` — pure `docker run` argv construction; the whole security
  posture lives in one reviewable, unit-testable place
- `runner.py` — executes the argv under a hard timeout, classifies the exit
  (`passed`/`failed`/`timed_out`/`error`), kills by name on timeout; both the
  subprocess runner and the killer are injectable, so every path is
  unit-testable without Docker
- `parser.py` — turns pytest's final summary line into counts, scanning from
  the end so a `print` inside a test cannot impersonate the summary

Integration tests run the real loop against Docker (green passes, red fails,
hung times out with no orphan left behind) and self-skip when Docker is
absent — which is why CI runs them on every push.

## Development

```sh
python -m venv .venv && .venv/bin/pip install -e . pytest
.venv/bin/pytest        # unit + integration (integration skips without Docker)
```

## Roadmap

- [ ] Per-test result extraction from the pytest report
- [ ] Custom sandbox images with extra preinstalled dependencies
- [ ] Podman support behind a `--runtime` flag

## License

[MIT](LICENSE) — Edwin Martinez
