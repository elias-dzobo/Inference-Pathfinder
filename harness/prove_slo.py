#!/usr/bin/env python3
"""Run a closed-loop load and exit 0 iff SLO thresholds pass.

Example:
  python3 harness/prove_slo.py --config configs/baseline.toml
  THREADS=2 python3 harness/prove_slo.py   # expect fail vs baseline SLO
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from client import one_request_stream, pct  # noqa: E402


def load_config(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def closed_samples(url: str, prompt: str, max_tokens: int, concurrency: int, waves: int) -> list[dict]:
    rows: list[dict] = []
    for _ in range(waves):
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futs = [
                ex.submit(one_request_stream, url, prompt, max_tokens, 0.0)
                for _ in range(concurrency)
            ]
            for fut in as_completed(futs):
                rows.append(fut.result())
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Prove or fail serving SLO")
    ap.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "configs" / "baseline.toml",
    )
    ap.add_argument("--url", default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    server = cfg.get("server", {})
    load = cfg.get("load", {})
    slo = cfg.get("slo", {})
    prompt_cfg = cfg.get("prompt", {})

    url = args.url or server.get("url", "http://127.0.0.1:8080/v1/chat/completions")
    prompt = prompt_cfg.get("text", "Say hello in one short sentence.")
    max_tokens = int(prompt_cfg.get("max_tokens", 32))
    concurrency = int(load.get("concurrency", 2))
    waves = int(load.get("waves", 3))
    warmup = int(load.get("warmup_waves", 1))

    ttft_limit = float(slo.get("ttft_p95_ms", 200))
    tpot_limit = float(slo.get("tpot_p95_ms", 40))

    print(f"config: {args.config}")
    print(f"load:   closed c={concurrency} waves={waves} (+{warmup} warmup)")
    print(f"SLO:    TTFT p95 ≤ {ttft_limit} ms  AND  TPOT p95 ≤ {tpot_limit} ms")

    # warmup discarded
    if warmup > 0:
        closed_samples(url, prompt, max_tokens, concurrency, warmup)

    rows = closed_samples(url, prompt, max_tokens, concurrency, waves)
    ttft = [r["ttfb_ms"] for r in rows]
    tpot = [r["tpot_ms"] for r in rows if r.get("tpot_ms") is not None]
    total = [r["total_ms"] for r in rows]

    ttft_p95 = pct(ttft, 95)
    tpot_p95 = pct(tpot, 95) if tpot else float("nan")
    print(f"n={len(rows)}")
    print(f"TTFT  p50={pct(ttft, 50):.1f}  p95={ttft_p95:.1f}  p99={pct(ttft, 99):.1f}")
    if tpot:
        print(f"TPOT  p50={pct(tpot, 50):.1f}  p95={tpot_p95:.1f}  p99={pct(tpot, 99):.1f}")
    print(f"total p50={pct(total, 50):.1f}  p95={pct(total, 95):.1f}")

    ok_ttft = ttft_p95 <= ttft_limit
    ok_tpot = tpot_p95 <= tpot_limit
    print("---")
    print(f"TTFT p95 {'PASS' if ok_ttft else 'FAIL'} ({ttft_p95:.1f} vs ≤ {ttft_limit})")
    print(f"TPOT p95 {'PASS' if ok_tpot else 'FAIL'} ({tpot_p95:.1f} vs ≤ {tpot_limit})")

    if ok_ttft and ok_tpot:
        print("SLO: PASS")
        return 0
    print("SLO: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
