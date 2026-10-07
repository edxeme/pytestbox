"""Parse pytest's final summary line into structured counts.

pytest prints a last line like ``3 passed in 0.02s`` or, without ``-q``,
``===== 1 failed, 2 passed in 0.03s =====``. This module turns whatever
variant appears in captured output into ``{"passed": 3}`` /
``{"failed": 1, "passed": 2}`` — and returns ``None`` when there is no
summary at all (crash, timeout, foreign output).
"""

from __future__ import annotations

import re

#: Counts pytest can report on its final line; ``warning`` is singular.
_KNOWN_COUNTS = {
    "passed",
    "failed",
    "error",
    "errors",
    "skipped",
    "xfailed",
    "xpassed",
    "warning",
    "warnings",
    "deselected",
}

_FINAL_LINE = re.compile(
    r"^[=\s]*(?P<counts>\d+ \w+(?:, \d+ \w+)*)(?:\s+in\s+[\d.]+s[^=]*)?[=\s]*$"
)


def parse_summary(output: str) -> dict[str, int] | None:
    """Extract pytest counts from *output*; ``None`` when nothing matches.

    Scans from the end: the summary is the last meaningful line, and
    earlier lines that merely look like summaries (e.g. inside tracebacks
    or captured prints) must not win.
    """
    for line in reversed(output.splitlines()):
        match = _FINAL_LINE.match(line.strip())
        if match is None:
            continue

        counts: dict[str, int] = {}
        for chunk in match.group("counts").split(", "):
            number, _, word = chunk.partition(" ")
            if word not in _KNOWN_COUNTS or not number.isdigit():
                counts = {}
                break
            counts[word] = counts.get(word, 0) + int(number)

        if counts:
            return counts
    return None
