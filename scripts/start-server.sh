#!/usr/bin/env bash
# Start llama-server for slo-pathfinder (CPU path).
# Override via env or source configs/baseline.env
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/configs/baseline.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "$ROOT/configs/baseline.env"
  set +a
fi

LLAMA_SERVER="${LLAMA_SERVER:-/Users/eliasdzobo/Desktop/2026/llama.cpp/build/bin/llama-server}"
MODEL="${MODEL:-/Users/eliasdzobo/Downloads/qwen3-0.6b-q4_k_m.gguf}"
THREADS="${THREADS:-4}"
CTX="${CTX:-2048}"
PORT="${PORT:-8080}"
HOST="${HOST:-127.0.0.1}"
NGL="${NGL:-0}"

if [[ ! -x "$LLAMA_SERVER" ]]; then
  echo "missing binary: $LLAMA_SERVER" >&2
  exit 1
fi
if [[ ! -f "$MODEL" ]]; then
  echo "missing model: $MODEL" >&2
  exit 1
fi

echo "server: $LLAMA_SERVER"
echo "model:  $MODEL"
echo "flags:  -t $THREADS -c $CTX -ngl $NGL --reasoning off --host $HOST --port $PORT"
exec "$LLAMA_SERVER" \
  -m "$MODEL" \
  -t "$THREADS" \
  -c "$CTX" \
  -ngl "$NGL" \
  --reasoning off \
  --host "$HOST" \
  --port "$PORT"
