#!/usr/bin/env python3
"""Print RSS MiB for a PID (macOS/Linux). Usage: rss_mb.py <pid>"""

from __future__ import annotations

import sys


def rss_mb(pid: int) -> float:
    # macOS: ps rss is in KB
    import subprocess

    out = subprocess.check_output(["ps", "-o", "rss=", "-p", str(pid)], text=True).strip()
    return int(out) / 1024.0


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: rss_mb.py <pid>")
    print(f"{rss_mb(int(sys.argv[1])):.1f}")


if __name__ == "__main__":
    main()
