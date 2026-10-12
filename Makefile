.PHONY: one prove-slo fail-slo sweep open2 open4 kv help

PYTHON ?= python3
URL ?= http://127.0.0.1:8080/v1/chat/completions

help:
	@echo "Targets: one prove-slo fail-slo sweep open2 open4 kv"
	@echo "Start server first: ./scripts/start-server.sh"

one:
	$(PYTHON) harness/client.py --url $(URL) --warmup 1 --repeats 3 --max-tokens 32

prove-slo:
	$(PYTHON) harness/prove_slo.py --config configs/baseline.toml --url $(URL)

fail-slo:
	@echo "Expecting SLO FAIL at concurrency=8..."
	@$(PYTHON) harness/prove_slo.py --config configs/stress-fail.toml --url $(URL); \
	status=$$?; \
	if [ $$status -eq 1 ]; then echo "OK: harness correctly reported FAIL"; exit 0; \
	elif [ $$status -eq 0 ]; then echo "Unexpected PASS — tighten load or SLO"; exit 1; \
	else exit $$status; fi

sweep:
	$(PYTHON) harness/slo_sweep.py --url $(URL) --mode closed --concurrency 1,2,4,8 --waves 3 --max-tokens 32

open2:
	$(PYTHON) harness/slo_sweep.py --url $(URL) --mode open --rate 2 --duration 20 --max-tokens 32

open4:
	$(PYTHON) harness/slo_sweep.py --url $(URL) --mode open --rate 4 --duration 20 --max-tokens 32

kv:
	$(PYTHON) harness/kv_estimate.py
