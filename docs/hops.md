# Hops

```
Client  →  HTTP API (llama-server)  →  Engine (llama.cpp)  →  Device (CPU)
 hop0              hop1                      hop2                  hop3
```

When a latency number moves, name the **hop** before blaming “the model.”

| Hop | Owns | Typical move |
|-----|------|--------------|
| 0 | Client timing / buffering | `--no-stream` collapses TTFT into total |
| 1 | Queue / admit | Concurrency ↑ → TTFT p95 ↑↑ |
| 2 | Prefill + decode orchestration | Long prompt, sampling |
| 3 | Matmul / memory bandwidth | `-t`, quant, KV length |

See also: `../writing/01-inference-request-lifecycle.md` in the parent `ai-infra` tree (or blog series).
