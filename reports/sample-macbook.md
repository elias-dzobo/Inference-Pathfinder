# Sample run — MacBook Pro (Intel), Qwen3-0.6B Q4_K_M, CPU

Flags: `-t 4 -c 2048 -ngl 0 --reasoning off`. Short prompt, `max_tokens=32` unless noted.

## Closed sweep (slo_sweep)

| c | TTFT p95 | TPOT p95 | total p95 |
|--:|---------:|---------:|----------:|
| 1 | 45.9 | 23.6 | 235 |
| 2 | 75.9 | 33.3 | 331 |
| 4 | 330 | 72.5 | 722 |
| 8 | 1066 | 91.8 | 1585 |

Baseline SLO (`TTFT p95≤200`, `TPOT p95≤40`) expected **PASS** at c=2, **FAIL** at c=8.

## Open loop

| rate | TTFT p95 | TPOT p95 | total p99 | ≈L=λW |
|-----:|---------:|---------:|----------:|------:|
| 2/s | 69 | 31 | 401 | ~0.6 |
| 4/s | 236 | 88 | 1068 | ~2.3 |

## KV RSS (idle after load)

| CTX | RSS MiB | Paper KV |
|----:|--------:|---------:|
| 2048 | 801 | 224 |
| 8192 | 1498 | 896 |
| 32768 | 4172 | 3584 |

Paper: 112 KiB/token (2×28×8×128×2).
