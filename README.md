# slo-pathfinder

**Serve one GGUF. Load-test it. Prove or fail an SLO.**

A small CPU-first inference harness built around [`llama-server`](https://github.com/ggml-org/llama.cpp) — not a chatbot UI. The point is judgment: hops, prefill vs decode, KV bytes, and percentile SLOs.

```
Client  →  llama-server  →  llama.cpp engine  →  CPU
 hop0         hop1              hop2             hop3
```

## Default SLO (tune in `configs/baseline.toml`)

```text
TTFT p95 ≤ 200 ms
TPOT p95 ≤ 40 ms
Load:     closed concurrency = 2
Server:   -t 4 -c 2048 -ngl 0 --reasoning off
```

`make prove-slo` exits **0** on pass, **1** on fail.

## Quick start

1. Build [llama.cpp](https://github.com/ggml-org/llama.cpp); download a small GGUF (e.g. Qwen3-0.6B Q4_K_M).
2. Configure paths:
   ```bash
   cp configs/baseline.env.example configs/baseline.env
   # edit LLAMA_SERVER and MODEL
   ```
3. Terminal A — server:
   ```bash
   ./scripts/start-server.sh
   ```
4. Terminal B — harness:
   ```bash
   make one          # single request (M1)
   make prove-slo    # pass/fail SLO (M2)
   make fail-slo     # same thresholds, c=8 — expect FAIL
   make sweep        # closed 1,2,4,8 percentiles
   ```

Requires Python 3.11+ (stdlib only: `tomllib`, `urllib`).

## Milestones

| | Demo |
|--|------|
| **M1** | `make one` — print TTFT / TPOT |
| **M2** | `make prove-slo` then `make fail-slo` (or `THREADS=2 ./scripts/start-server.sh` and re-prove) |
| **M3** | `make kv` + RSS at `CTX=2048` vs `8192` — see [docs/kv.md](docs/kv.md) |
| **M4** | `make open2` / `make open4` vs closed — [docs/load.md](docs/load.md) |

## Docs

- [docs/hops.md](docs/hops.md) — which hop owns the time  
- [docs/phases.md](docs/phases.md) — TTFT vs TPOT  
- [docs/kv.md](docs/kv.md) — KV as a RAM lease  
- [docs/load.md](docs/load.md) — closed vs open, Little’s law  

Sample numbers from a MacBook CPU run: [reports/sample-macbook.md](reports/sample-macbook.md)

## Layout

```
harness/          client, sweeps, prove_slo, kv_estimate
configs/          baseline.toml, stress-fail.toml, baseline.env.example
scripts/          start-server.sh
docs/             conceptual notes
reports/          checked-in sample results
```

## License

MIT
