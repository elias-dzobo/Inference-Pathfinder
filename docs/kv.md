# KV as capacity

```
bytes/token = 2 × n_layer × n_kv_head × head_dim × elem_bytes
```

For Qwen3-0.6B (28 / 8 / 128 / f16): **114688 B = 112 KiB per token** (one sequence).

```bash
python3 harness/kv_estimate.py
CTX=2048 ./scripts/start-server.sh   # then harness/rss_mb.py $(pgrep -n llama-server)
CTX=8192 ./scripts/start-server.sh   # ΔRSS should ≈ paper ΔKV (~672 MiB)
```

Raising `-c` leases RAM. That is a capacity incident, not “mysterious slowness.”
