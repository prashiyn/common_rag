#!/bin/sh
# Manual / on-demand model pull (Compose profile `ollama-bootstrap`, service `ollama_init`).
# Not run on every `docker compose up` — invoke explicitly when you need pulls.
#
# OLLAMA_PULL_MODELS     — comma-separated list (repo-root .env)
# OLLAMA_PULL_MODELS_EXTRA — optional; merged for one-off pulls without editing .env
#
# Skips any model already present; only missing models are downloaded.
set -eu

OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
export OLLAMA_HOST

MODELS="${OLLAMA_PULL_MODELS:-}"
if [ -n "${OLLAMA_PULL_MODELS_EXTRA:-}" ]; then
  if [ -n "$MODELS" ]; then
    MODELS="${MODELS},${OLLAMA_PULL_MODELS_EXTRA}"
  else
    MODELS="${OLLAMA_PULL_MODELS_EXTRA}"
  fi
fi

echo "Waiting for Ollama at ${OLLAMA_HOST}..."
attempt=0
until ollama list >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "${attempt}" -gt 90 ]; then
    echo "Ollama not ready after 90 attempts" >&2
    exit 1
  fi
  sleep 2
done

if [ -z "$MODELS" ]; then
  echo "No models requested (OLLAMA_PULL_MODELS / OLLAMA_PULL_MODELS_EXTRA empty)."
  exit 0
fi

echo "$MODELS" | tr ',' '\n' | while IFS= read -r model; do
  model=$(printf '%s' "$model" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  [ -z "$model" ] && continue
  if ollama show "$model" >/dev/null 2>&1; then
    echo "Already present, skipping: ${model}"
    continue
  fi
  echo "Pulling ${model}..."
  ollama pull "$model"
done

echo "Done. (Only missing models are downloaded; existing models on the volume are left unchanged.)"
