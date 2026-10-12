#!/usr/bin/env python3
"""Paper estimate of KV cache bytes for Qwen3-0.6B (from GGUF metadata).

Run AFTER you fill PREDICT D0 by hand — this is the answer key, not a substitute.
"""

from __future__ import annotations

# From qwen3-0.6b-q4_k_m.gguf (llama-cli --verbose):
N_LAYER = 28
N_KV_HEAD = 8  # GQA (attention.head_count=16, head_count_kv=8)
HEAD_DIM = 128  # attention.key_length / value_length
ELEM_BYTES = 2  # f16 KV (llama.cpp default cache type unless -ctk/-ctv override)


def bytes_per_token(elem_bytes: int = ELEM_BYTES) -> int:
    # 2 = K and V
    return 2 * N_LAYER * N_KV_HEAD * HEAD_DIM * elem_bytes


def main() -> None:
    bpt = bytes_per_token()
    print(f"arch: layers={N_LAYER} kv_heads={N_KV_HEAD} head_dim={HEAD_DIM} elem={ELEM_BYTES}B")
    print(f"KV bytes / token / sequence = {bpt} B = {bpt / 1024:.2f} KiB")
    print()
    print(f"{'ctx':>8} {'1 seq MiB':>12} {'4 seq MiB':>12}")
    for ctx in (512, 2048, 8192, 32768):
        one = ctx * bpt / (1024 * 1024)
        four = 4 * one
        print(f"{ctx:8d} {one:12.2f} {four:12.2f}")


if __name__ == "__main__":
    main()
