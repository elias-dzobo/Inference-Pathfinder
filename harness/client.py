#!/usr/bin/env python3
"""Thin HTTP client for slo-pathfinder — timings only, no framework.

Default: stream=True so TTFB ≈ time to first token (TTFT proxy).
Non-stream JSON often buffers the whole completion before headers finish,
which collapses TTFB into total — useful as a teaching contrast (--no-stream).
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


DEFAULT_URL = "http://127.0.0.1:8080/v1/chat/completions"
DEFAULT_PROMPT = "Say hello in one short sentence."


def one_request_stream(
    url: str,
    prompt: str,
    max_tokens: int,
    delay_before_read_ms: float = 0.0,
) -> dict:
    body = json.dumps(
        {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0,
            "stream": True,
        }
    ).encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()
    t_first = None
    pieces: list[str] = []
    completion_tokens = 0

    with urllib.request.urlopen(req, timeout=600) as resp:
        if delay_before_read_ms > 0:
            time.sleep(delay_before_read_ms / 1000.0)
        while True:
            line = resp.readline()
            if not line:
                break
            line = line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            choice = (chunk.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}
            # Qwen3 / reasoning models stream into reasoning_content first;
            # content may stay empty until the think budget is spent.
            piece = delta.get("content") or delta.get("reasoning_content")
            if piece:
                if t_first is None:
                    t_first = time.perf_counter()
                pieces.append(piece)
                completion_tokens += 1
            usage = chunk.get("usage") or {}
            if usage.get("completion_tokens"):
                completion_tokens = usage["completion_tokens"]

    t_done = time.perf_counter()
    if t_first is None:
        t_first = t_done

    n = completion_tokens or len(pieces)
    ttfb_ms = (t_first - t0) * 1000
    total_ms = (t_done - t0) * 1000
    body_ms = (t_done - t_first) * 1000
    decode_s = max(t_done - t_first, 1e-9)
    tok_s = n / decode_s if n else None
    # TPOT: ms per token after the first (S2 definition)
    tpot_ms = body_ms / max(n - 1, 1) if n else None
    text = "".join(pieces).replace("\n", " ")[:120]

    return {
        "mode": "stream",
        "ttfb_ms": ttfb_ms,
        "ttft_ms": ttfb_ms,
        "tpot_ms": tpot_ms,
        "total_ms": total_ms,
        "body_ms": body_ms,
        "prompt_tokens": None,
        "completion_tokens": n,
        "tok_s_body": tok_s,
        "text": text,
    }


def one_request_buffered(
    url: str,
    prompt: str,
    max_tokens: int,
    delay_before_read_ms: float = 0.0,
) -> dict:
    body = json.dumps(
        {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0,
            "stream": False,
        }
    ).encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as resp:
        t_headers = time.perf_counter()
        if delay_before_read_ms > 0:
            time.sleep(delay_before_read_ms / 1000.0)
        raw = resp.read()
        t_done = time.perf_counter()

    payload = json.loads(raw)
    try:
        msg = payload["choices"][0]["message"]
        text = msg.get("content") or msg.get("reasoning_content") or ""
    except (KeyError, IndexError, TypeError):
        text = json.dumps(payload)[:200]

    usage = payload.get("usage") or {}
    completion_tokens = usage.get("completion_tokens")
    prompt_tokens = usage.get("prompt_tokens")
    timings = payload.get("timings") or {}

    ttfb_ms = (t_headers - t0) * 1000
    total_ms = (t_done - t0) * 1000
    body_ms = (t_done - t_headers) * 1000
    decode_s = max(t_done - t_headers, 1e-9)
    tok_s = completion_tokens / decode_s if completion_tokens else None

    n = completion_tokens or 0
    pred_ms = timings.get("predicted_ms")
    tpot_ms = None
    if pred_ms is not None and n > 1:
        tpot_ms = pred_ms / (n - 1)
    elif pred_ms is not None and n == 1:
        tpot_ms = pred_ms

    return {
        "mode": "buffered",
        "ttfb_ms": ttfb_ms,
        "ttft_ms": timings.get("prompt_ms"),  # server prefill proxy when buffered
        "tpot_ms": tpot_ms,
        "total_ms": total_ms,
        "body_ms": body_ms,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tok_s_body": tok_s,
        "text": text.replace("\n", " ")[:120],
        "server_prompt_ms": timings.get("prompt_ms"),
        "server_predicted_ms": timings.get("predicted_ms"),
        "server_predicted_per_second": timings.get("predicted_per_second"),
    }


def pct(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    k = (len(ys) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ys) - 1)
    return ys[f] + (ys[c] - ys[f]) * (k - f)


def main() -> None:
    ap = argparse.ArgumentParser(description="pathfinder S1 client")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument(
        "--prompt-file",
        default=None,
        help="Read prompt text from file (S2 C1 long prompt)",
    )
    ap.add_argument("--max-tokens", type=int, default=64)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument(
        "--delay-before-read-ms",
        type=float,
        default=0.0,
        help="B3 E2: sleep before consuming the body",
    )
    ap.add_argument("--warmup", type=int, default=0, help="discard N runs first")
    ap.add_argument(
        "--no-stream",
        action="store_true",
        help="buffered JSON (TTFB often ≈ total — teaching contrast)",
    )
    args = ap.parse_args()
    prompt = args.prompt
    if args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read().strip()

    runner = one_request_buffered if args.no_stream else one_request_stream

    def run_one(_: int) -> dict:
        return runner(
            args.url,
            prompt,
            args.max_tokens,
            args.delay_before_read_ms,
        )

    total_runs = args.warmup + args.repeats
    results: list[dict] = []

    if args.concurrency <= 1:
        for i in range(total_runs):
            try:
                r = run_one(i)
            except urllib.error.URLError as e:
                raise SystemExit(
                    f"request failed: {e}\nIs llama-server up? ./scripts/start-server.sh"
                ) from e
            if i >= args.warmup:
                results.append(r)
                tok_s = (
                    f"tok/s≈{r['tok_s_body']:.2f} "
                    if r["tok_s_body"] is not None
                    else ""
                )
                extra = ""
                if r.get("server_predicted_per_second") is not None:
                    extra = (
                        f" srv_pp={r.get('server_prompt_ms'):.1f}ms"
                        f" srv_tg={r.get('server_predicted_ms'):.1f}ms"
                        f" srv_tok/s={r['server_predicted_per_second']:.1f}"
                    )
                tpot = (
                    f"TPOT={r['tpot_ms']:.1f}ms "
                    if r.get("tpot_ms") is not None
                    else ""
                )
                ttft = r["ttft_ms"] if r.get("ttft_ms") is not None else r["ttfb_ms"]
                print(
                    f"run {i - args.warmup + 1} [{r['mode']}]: "
                    f"TTFT={ttft:.1f}ms "
                    f"{tpot}"
                    f"total={r['total_ms']:.1f}ms "
                    f"body={r['body_ms']:.1f}ms "
                    f"tok={r['completion_tokens']} {tok_s}"
                    f"{extra} | {r['text']}"
                )
    else:
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futs = [ex.submit(run_one, i) for i in range(args.concurrency)]
            for fut in as_completed(futs):
                r = fut.result()
                results.append(r)
                print(
                    f"[{r['mode']}] ttfb={r['ttfb_ms']:.1f}ms "
                    f"total={r['total_ms']:.1f}ms tok={r['completion_tokens']} "
                    f"| {r['text']}"
                )

    if len(results) > 1:
        totals = [r["total_ms"] for r in results]
        ttfbs = [r["ttfb_ms"] for r in results]
        print("---")
        print(
            f"n={len(results)}  "
            f"ttfb p50={pct(ttfbs, 50):.1f} p99={pct(ttfbs, 99):.1f}  "
            f"total p50={pct(totals, 50):.1f} p99={pct(totals, 99):.1f}  "
            f"mean_total={statistics.mean(totals):.1f}"
        )


if __name__ == "__main__":
    main()
