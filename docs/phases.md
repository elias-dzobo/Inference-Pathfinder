# Prefill vs decode (TTFT / TPOT)

| Phase | Job | Metric |
|-------|-----|--------|
| Prefill | Read prompt, write KV | **TTFT** ≈ stream time to first token |
| Decode | Emit tokens | **TPOT** ≈ `body_ms / max(n-1, 1)` |

```
total ≈ TTFT + (n − 1) × TPOT
```

Use **actual** `n`, not `max_tokens`. Long prompts raise TTFT *and* can raise TPOT (attend over longer KV).
