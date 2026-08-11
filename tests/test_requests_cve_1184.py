#!/usr/bin/env python3
"""Regression test for CVE-2024-47081 (GHSA-9hjg-9r4m-mvj7).

requests < 2.32.4 can leak .netrc credentials to a different host when it
follows a redirect to a URL carrying userinfo. The pinned dependency set in
requirements.txt must never resolve to an affected requests version.

See https://github.com/Pythagora-io/gpt-pilot/issues/1184

Runnable two ways:
  * as a standalone script:  python3 tests/test_requests_cve_1184.py
  * under pytest:            pytest tests/test_requests_cve_1184.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIREMENTS = Path(__file__).resolve().parent.parent / "requirements.txt"
# First requests release that fixes CVE-2024-47081.
CVE_FIXED = (2, 32, 4)


def _parse_version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.strip().split("."))


def _requests_pin() -> tuple[str, tuple[int, ...]]:
    """Return the (operator, version) of the requests pin in requirements.txt."""
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[=<>!~ ]", line, maxsplit=1)[0].split("[", 1)[0].lower()
        if name == "requests":
            match = re.search(r"(==|>=|~=|<|<=|>|!=)\s*(\d+(?:\.\d+)*)", line)
            if match:
                return match.group(1), _parse_version(match.group(2))
            raise AssertionError(f"requests has no version pin in requirements.txt: {line!r}")
    raise AssertionError("requests is not pinned in requirements.txt")


def test_requests_pin_not_affected_by_cve_2024_47081() -> None:
    operator, version = _requests_pin()
    if operator in ("==", ">=", "~=") and version >= CVE_FIXED:
        return
    if operator == ">" and version >= (2, 32, 3):
        # ">2.32.3" already excludes 2.32.3, so only fixed releases can be resolved.
        return
    raise AssertionError(
        f"requests pin {operator}{'.'.join(map(str, version))} can still resolve to a "
        "version affected by CVE-2024-47081 (GHSA-9hjg-9r4m-mvj7); bump to "
        "requests>=2.32.4"
    )


if __name__ == "__main__":
    try:
        test_requests_pin_not_affected_by_cve_2024_47081()
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
    print("OK: requests pin is not affected by CVE-2024-47081")
