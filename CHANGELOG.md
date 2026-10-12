# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] — 2026-10-12

### Added

- `pytestbox build-image` — generates and builds the offline sandbox image
  (python slim + pytest, nothing else) so sandboxes run with `--network none`.
- Docker image for pytestbox itself and a bundled sample suite.
- Docker integration tests: green passes, red fails, hung times out and
  leaves no orphaned container (self-skip without Docker).
- GitHub Actions CI: pytest 3.11–3.13 with integration plus a sandbox smoke run.
- Full documentation: security posture, exit-code contract, architecture.

### Fixed

- `build-image --python 3.12` now tags `pytestbox:py312` (dots stripped) so
  the default `run` image always matches what was built.

## [0.1.1] — 2026-10-10

### Fixed

- Host-side timeout now kills the sandbox container **by name** — killing the
  docker client alone left hung suites running as orphaned containers.

## [0.1.0] — 2026-10-08

### Added

- `pytestbox run PATH [--json] [--timeout N] [-- CMD...]`: untrusted suites in
  locked-down containers — no network, read-only filesystem, memory/CPU/PID
  caps, dropped capabilities, host-enforced hard timeout.
- Structured `SandboxResult`: status (`passed`/`failed`/`timed_out`/`error`),
  exit code, duration and parsed pytest counts.
- CI-ready exit codes: 0 green, 1 tests red, 2 timed out, 3 sandbox malfunction.
- Summary parsing scanned from the end of the output so a print inside a test
  cannot impersonate pytest's summary line.
