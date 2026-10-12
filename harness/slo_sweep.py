#!/usr/bin/env python3
"""S4 — concurrency / open-loop sweep with TTFT & TPOT percentiles.

Examples:
  python3 scripts/slo_sweep.py --mode closed --concurrency 1,2,4,8 --waves 3
  python3 scripts/slo_sweep.py --mode open --rate 2 --duration 20
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# allow importing client helpers from this package dir
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from client import DEFAULT_PROMPT, DEFAULT_URL, one_request_stream, pct  # noqa: E402


def summarize(label: str, rows: list[dict]) -> None:
    if not rows:
        print(f"{label}: no samples")
        return
    ttft = [r["ttfb_ms"] for r in rows]
    tpot = [r["tpot_ms"] for r in rows if r.get("tpot_ms") is not None]
    total = [r["total_ms"] for r in rows]
    print(f"\n=== {label}  n={len(rows)} ===")
    print(
        f"TTFT  p50={pct(ttft, 50):.1f}  p95={pct(ttft, 95):.1f}  p99={pct(ttft, 99):.1f}"
    )
    if tpot:
        print(
            f"TPOT  p50={pct(tpot, 50):.1f}  p95={pct(tpot, 95):.1f}  p99={pct(tpot, 99):.1f}"
        )
    print(
        f"total p50={pct(total, 50):.1f}  p95={pct(total, 95):.1f}  p99={pct(total, 99):.1f}  "
        f"mean={statistics.mean(total):.1f}"
    )


def closed_wave(url: str, prompt: str, max_tokens: int, concurrency: int) -> list[dict]:
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = [
            ex.submit(one_request_stream, url, prompt, max_tokens, 0.0)
            for _ in range(concurrency)
        ]
        for fut in as_completed(futs):
            rows.append(fut.result())
    return rows


def run_closed(
    url: str,
    prompt: str,
    max_tokens: int,
    levels: list[int],
    waves: int,
    warmup_waves: int,
) -> None:
    for c in levels:
        kept: list[dict] = []
        for w in range(warmup_waves + waves):
            batch = closed_wave(url, prompt, max_tokens, c)
            if w >= warmup_waves:
                kept.extend(batch)
        summarize(f"closed c={c}", kept)


def run_open(
    url: str,
    prompt: str,
    max_tokens: int,
    rate: float,
    duration: float,
) -> None:
    """Open loop: schedule starts at fixed rate; late dispatch still counts in latency."""
    n = max(1, int(rate * duration))
    t0 = time.perf_counter()
    rows: list[dict] = []

    def one(i: int) -> dict:
        intended = t0 + i / rate
        now = time.perf_counter()
        if intended > now:
            time.sleep(intended - now)
        # latency from intended send (coordinated-omission aware)
        start = time.perf_counter()
        r = one_request_stream(url, prompt, max_tokens, 0.0)
        # rewrite total relative to intended schedule
        wall = (time.perf_counter() - intended) * 1000
        r = dict(r)
        r["total_ms"] = wall
        r["schedule_lag_ms"] = (start - intended) * 1000
        return r

    with ThreadPoolExecutor(max_workers=min(32, n)) as ex:
        futs = [ex.submit(one, i) for i in range(n)]
        for fut in as_completed(futs):
            rows.append(fut.result())

    summarize(f"open rate={rate}/s duration={duration}s", rows)
    lags = [r.get("schedule_lag_ms", 0.0) for r in rows]
    print(
        f"sched_lag p50={pct(lags, 50):.1f}  p95={pct(lags, 95):.1f}  "
        f"(how late starts were vs intended)"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="S4 SLO sweep")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--max-tokens", type=int, default=32)
    ap.add_argument("--mode", choices=("closed", "open"), default="closed")
    ap.add_argument(
        "--concurrency",
        default="1,2,4,8",
        help="closed mode: comma-separated concurrency levels",
    )
    ap.add_argument("--waves", type=int, default=3, help="closed: measured waves per level")
    ap.add_argument("--warmup-waves", type=int, default=1)
    ap.add_argument("--rate", type=float, default=2.0, help="open: requests per second")
    ap.add_argument("--duration", type=float, default=20.0, help="open: seconds")
    args = ap.parse_args()

    if args.mode == "closed":
        levels = [int(x) for x in args.concurrency.split(",") if x.strip()]
        run_closed(
            args.url,
            args.prompt,
            args.max_tokens,
            levels,
            args.waves,
            args.warmup_waves,
        )
    else:
        run_open(args.url, args.prompt, args.max_tokens, args.rate, args.duration)


if __name__ == "__main__":
    main()
