# Docker Compose runbook

This repo provides two Docker Compose entry points:

- `docker-compose.yml` for regular/local "live" usage.
- `docker-compose-test.yaml` for isolated test runs with different host ports and `./test_db/*` volumes.

The **unified API** (`unified_api`) exposes all seven merged application services on one port. See [unified-api/README.md](./unified-api/README.md) for route prefixes.

## Prerequisites

- Docker Engine + Docker Compose v2.
- Repo-root `.env` created from `.env.example`.
- `NEO4J_PASSWORD` must be non-default (do not use `neo4j`).

## 1) Prepare env

From repo root:

```bash
cp .env.example .env
```

Set at least:

- `POSTGRES_PASSWORD`
- `NEO4J_USERNAME` (usually `neo4j`)
- `NEO4J_PASSWORD` (non-default)

## 2) Refresh images to latest code

Use `--build` when you changed code or Dockerfiles. Use `build --pull` to refresh base images too.

### Faster rebuilds (layer cache)

The `unified_api/Dockerfile.compose` installs dependencies in two steps:

1. Copy only `pyproject.toml` + `uv.lock` (+ readme if required) → `uv sync --frozen --no-dev --no-install-project`
2. Copy application source → `uv sync --frozen --no-dev`

**Dependency downloads are reused** until the lockfile changes. Code-only edits skip the heavy download step.

Requires **BuildKit** (default in recent Docker):

```bash
export DOCKER_BUILDKIT=1
```

Avoid `docker compose build --no-cache` unless debugging. Prefer `docker compose build unified_api` for a single service.

After changing `pyproject.toml` or `uv.lock`, commit the updated lockfile and rebuild.

### Live stack images

```bash
docker compose --env-file .env build --pull unified_api
```

### Test stack images

```bash
docker compose -f docker-compose-test.yaml --env-file .env build --pull unified_api
```

Optional clean rebuild (slow):

```bash
docker compose -f docker-compose-test.yaml --env-file .env build --no-cache unified_api
```

## 3) Run startup-order smoke test (focused)

This validates dependency ordering: `ollama` → `unified_api` (which depends on postgres, neo4j, chroma).

**Before this smoke test:** complete [Ollama first-time setup](#ollama-first-time-setup-required-once-per-stack) on the **test** stack (pull models into `./test_db/ollama_data`).

```bash
# Start from clean state for test stack
docker compose -f docker-compose-test.yaml --env-file .env down

# 0) Ollama + model pull (skip if already done for this test volume)
docker compose -f docker-compose-test.yaml --env-file .env up -d ollama
docker compose -f docker-compose-test.yaml --env-file .env --profile ollama-bootstrap run --rm ollama_init

# 1) Build and start unified API (pulls postgres, neo4j, chroma via depends_on)
docker compose -f docker-compose-test.yaml --env-file .env build unified_api
docker compose -f docker-compose-test.yaml --env-file .env up -d unified_api
docker compose -f docker-compose-test.yaml --env-file .env ps

# 2) Health checks (test stack host port 18000)
curl -fsS http://127.0.0.1:18000/health
curl -fsS http://127.0.0.1:18000/llm-service/health
curl -fsS http://127.0.0.1:18000/doc-processing/health
curl -fsS http://127.0.0.1:18000/core-rag/health
curl -fsS http://127.0.0.1:18000/ra-literag/health
curl -fsS http://127.0.0.1:18000/temporal-graph/health
curl -fsS http://127.0.0.1:18000/temporal-graph-openai/health
curl -fsS http://127.0.0.1:18000/temporal-graph-traversal/health
```

If a health endpoint fails in a given branch, use `/docs` for basic server-up verification:

```bash
curl -I http://127.0.0.1:18000/docs
```

## 4) Run full stacks

On a **new machine** or **fresh** `./db/ollama_data` / `./test_db/ollama_data` volume, run [Ollama first-time setup](#ollama-first-time-setup-required-once-per-stack) **before** relying on Ollama-backed models in `doc_processing` or `llm-service`.

### Live stack

```bash
docker compose --env-file .env up -d
docker compose --env-file .env ps
```

Unified API: `http://127.0.0.1:8000` — `fin_rag` remains on port **6005**.

### Test stack

```bash
docker compose -f docker-compose-test.yaml --env-file .env up -d
docker compose -f docker-compose-test.yaml --env-file .env ps
```

Unified API: `http://127.0.0.1:18000` — `fin_rag` on **16005**.

## 5) Stop stacks

```bash
# Live
docker compose --env-file .env down

# Test
docker compose -f docker-compose-test.yaml --env-file .env down
```

## Compose file differences (expected)

- `docker-compose.yml`
  - Live host ports (`unified_api` → **8000**).
  - `./db/*` persistent data paths.
  - Explicit `container_name` values.
- `docker-compose-test.yaml`
  - Non-conflicting host ports (`unified_api` → **18000**).
  - `./test_db/*` isolated test data paths.
  - Project name `common-test` and no fixed container names.

Service graph, dependency ordering, and environment wiring are intended to stay in sync between both files.

## Ollama (in Compose)

Both compose files include **`ollama`** (`ollama/ollama:latest`). The unified API uses `OLLAMA_API_BASE=http://ollama:11434` for `llm-service` and `OLLAMA_BASE_URL` for `doc_processing` Docling VLM.

| Stack | Compose file | Host port (from your machine) | Model data on disk |
|-------|----------------|-------------------------------|---------------------|
| Live | `docker-compose.yml` | `11434` | `./db/ollama_data` |
| Test | `docker-compose-test.yaml` | `11435` | `./test_db/ollama_data` |

Inside the Docker network, apps always call **`http://ollama:11434`** (not `localhost`).

Model downloads are **not** run on every `docker compose up`. The service **`ollama_init`** (profile **`ollama-bootstrap`**) pulls models on demand. Already-downloaded models on the volume are **skipped**; only missing ones are fetched.

Default model list (override in repo-root `.env` as `OLLAMA_PULL_MODELS`):

- `nomic-embed-text-v2-moe:latest`
- `ibm/granite3.3-vision:2b`
- `ibm/granite-docling:latest`
- `glm-ocr:latest`
- `deepseek-ocr:latest`

**Live and test stacks use separate volumes** — you must run first-time setup **once per stack** if you use both.

---

### Ollama first-time setup (required once per stack)

Do this after `cp .env.example .env` and before expecting Docling/OCR models to work.

**1. Set models in repo-root `.env`** (already in `.env.example`):

```bash
OLLAMA_PULL_MODELS=nomic-embed-text-v2-moe:latest,ibm/granite3.3-vision:2b,ibm/granite-docling:latest,glm-ocr:latest,deepseek-ocr:latest
```

**2. Live stack — start Ollama and pull models** (can take a long time; large downloads):

```bash
docker compose --env-file .env up -d ollama
docker compose --env-file .env --profile ollama-bootstrap run --rm ollama_init
```

**3. Test stack** (same steps, different file and volume):

```bash
docker compose -f docker-compose-test.yaml --env-file .env up -d ollama
docker compose -f docker-compose-test.yaml --env-file .env --profile ollama-bootstrap run --rm ollama_init
```

**4. Verify models are present** (see [Verify installed models](#verify-installed-models)). Example for test stack:

```bash
docker compose -f docker-compose-test.yaml --env-file .env exec ollama ollama list
```

You should see names such as `ibm/granite-docling:latest`. If a model is missing, `doc_processing` will error with `model '...' not found`.

**5. Start the rest of the stack** (no model re-download):

```bash
# Live
docker compose --env-file .env up -d

# Test
docker compose -f docker-compose-test.yaml --env-file .env up -d
```

---

### Verify installed models

List models in the running Ollama container:

```bash
# Live
docker compose --env-file .env exec ollama ollama list

# Test
docker compose -f docker-compose-test.yaml --env-file .env exec ollama ollama list
```

Check a specific model:

```bash
docker compose -f docker-compose-test.yaml --env-file .env exec ollama ollama show ibm/granite-docling:latest
```

From the host (HTTP API):

```bash
# Live — port 11434
curl -s http://127.0.0.1:11434/api/tags

# Test — port 11435
curl -s http://127.0.0.1:11435/api/tags
```

---

### Add a new Ollama model later

Only models **not** already on that stack's volume are downloaded. Existing models are not re-pulled.

**Step 1 — Choose how to name the model**

- **Option A (recommended):** Add the model id to `OLLAMA_PULL_MODELS` in repo-root `.env` (comma-separated), so it is part of your documented set.

  ```bash
  # Example: append to the existing line in .env
  OLLAMA_PULL_MODELS=...,my-new-model:latest
  ```

- **Option B (one-off):** Pull a single model without editing `.env` using `OLLAMA_PULL_MODELS_EXTRA`.

**Step 2 — Ensure Ollama is running**

```bash
# Live
docker compose --env-file .env up -d ollama

# Test
docker compose -f docker-compose-test.yaml --env-file .env up -d ollama
```

**Step 3 — Pull (incremental)**

```bash
# Live — Option A (uses OLLAMA_PULL_MODELS from .env)
docker compose --env-file .env --profile ollama-bootstrap run --rm ollama_init

# Live — Option B (one model only)
docker compose --env-file .env --profile ollama-bootstrap run --rm \
  -e OLLAMA_PULL_MODELS_EXTRA=my-new-model:latest ollama_init
```

Test stack: add `-f docker-compose-test.yaml` to the same commands.

**Alternative — pull directly in the running container:**

```bash
docker compose -f docker-compose-test.yaml --env-file .env exec ollama ollama pull my-new-model:latest
```

**Step 4 — Verify**

```bash
docker compose -f docker-compose-test.yaml --env-file .env exec ollama ollama list
```

**Step 5 — Use the model**

- Register or reference the model in `doc_processing` config (e.g. `llm_config.yaml`) or `llm-service` config as needed.
- Restart the unified API if it caches model lists at startup:

  ```bash
  docker compose -f docker-compose-test.yaml --env-file .env up -d --force-recreate unified_api
  ```

---

### Normal stack start (no model download)

After first-time setup, daily use does **not** re-download models:

```bash
docker compose --env-file .env up -d
```

---

### Start order

`ollama` (healthy) → `unified_api` (depends on postgres, neo4j, chroma, ollama). Model pull (`ollama_init`) is **manual**, not part of `up`.

---

### Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| `model 'ibm/granite-docling:latest' not found` | Models never pulled on **this** stack's volume | Run [first-time setup](#ollama-first-time-setup-required-once-per-stack) or [add a new model](#add-a-new-ollama-model-later) |
| `Connection refused` to `localhost:11434` in `doc_processing` | Wrong URL inside container | Compose should set `OLLAMA_BASE_URL=http://ollama:11434`; recreate `unified_api` |
| Model on live stack but not test | Separate `./db/ollama_data` vs `./test_db/ollama_data` | Run `ollama_init` for the stack you are using |

---

### GPU (optional)

Uncomment the `deploy.resources` block under `ollama` in `docker-compose.yml` if you use the NVIDIA Container Toolkit.

## Logs: where output goes

### Default (all containers)

Anything written to **stdout** or **stderr** inside a container is collected by Docker's logging driver (usually `json-file`). You view it with:

```bash
docker compose --env-file .env logs -f unified_api
docker compose -f docker-compose-test.yaml --env-file .env logs -f unified_api
```

When you run `docker compose up` **without** `-d`, the same streams are multiplexed to your terminal.

### Application services (files on disk)

For `unified_api`, Compose bind-mounts **`unified_api/logs` on the host** to **`/app/logs` in the container**:

- Uvicorn access and server messages are appended to **`uvicorn.log`** (via `tee`, so `docker compose logs` still works).
- `core_rag_graph` also writes app log files under `/app/logs` (e.g. `graph.log`) from its logger.

`fin_rag` (separate service) writes **`server.log`**, **`low_rating_feedback.jsonl`**, and migration output **`alembic-migrate.log`** under **`fin_rag/logs/`**.

### Databases and Chroma

- **Postgres**: main logs live under the Postgres data volume (e.g. `./db/postgres_data` or `./test_db/postgres_data`). Use `docker compose logs postgres` for container stdout.
- **Neo4j**: debug/query logs can appear under the mounted `./db/neo4j_data/logs` or `./test_db/neo4j_data/logs` (see compose `volumes`). Use `docker compose logs neo4j` as well.
- **Chroma**: use `docker compose logs chroma`; persistence is under the chroma data volume paths in compose.
