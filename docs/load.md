# Load, concurrency, and SLOs

| Mode | Meaning |
|------|---------|
| **Closed** `c=N` | Always N requests in flight |
| **Open** `rate=λ` | Start requests on a timer; backlog can grow |

Little’s law: \(L ≈ λ × W\). **Rate is not concurrency.**  
Open @ 2/s with W≈0.28 s ⇒ L≈0.56 — lighter than closed c=2.

Optimize **goodput under SLO** (e.g. TTFT p95 ≤ 200 ms), not max `c`.

```bash
python3 harness/slo_sweep.py --mode closed --concurrency 1,2,4,8 --waves 3
python3 harness/slo_sweep.py --mode open --rate 2 --duration 20
python3 harness/slo_sweep.py --mode open --rate 4 --duration 20
```
