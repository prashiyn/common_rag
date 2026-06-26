# Repository layout decision

**Status:** Active (Option A)  
**Decided:** June 2026  
**Revisit:** After unified API migration and `fin_rag` integration are stable

## Decision

Keep service packages at the **repository root** with their historical directory names. Do **not** move code under a `packages/` tree or collapse all configuration into a single root `.env` while migration is still in progress.

This is **Option A** from the post-consolidation layout review.

## Rationale

- `unified_api` path dependencies, `Dockerfile.compose`, and `docker-compose.yml` already reference the current locations.
- Per-service `.env` files and compose `env_file` entries match how teams developed each service as standalone repos.
- A `packages/` rename or env consolidation is mostly cosmetic but touches many files (pyproject paths, Docker `COPY`, volume mounts, CI, docs). That churn is not worth it mid-migration.
- Standalone GitHub repos have been absorbed into [`common_rag`](https://github.com/prashiyn/common_rag); the in-tree paths intentionally mirror the old repo names for traceability.

## Current layout

```
common/
├── unified_api/              # Single FastAPI process (port 8000)
├── llm-service/
├── doc_processing/
├── core_rag_graph/
├── ra_literag/
├── temporial_graph/
├── temporial_graph_openai/
├── temporial_graph_traversal/   # Python package: raqe/
├── fin_rag/                     # Separate service (port 6005), not merged into unified_api
├── docs/                        # Canonical documentation
├── docker-compose.yml
├── docker-compose-test.yaml
├── .env                         # Local secrets (gitignored)
└── .env.example                 # Root template
```

### Path → unified API prefix

| Directory | API prefix | Notes |
|-----------|------------|--------|
| `llm-service/` | `/llm-service` | In-process when `LLM_CLIENT_MODE=inprocess` |
| `doc_processing/` | `/doc-processing` | |
| `core_rag_graph/` | `/core-rag` | |
| `ra_literag/` | `/ra-literag` | |
| `temporial_graph/` | `/temporal-graph` | Directory name retains historical typo |
| `temporial_graph_openai/` | `/temporal-graph-openai` | |
| `temporial_graph_traversal/` | `/temporal-graph-traversal` | |
| `fin_rag/` | — | Standalone; calls unified API for LLM |

### Configuration today

- **Root** `.env` / `.env.example` — shared infrastructure (Postgres, Neo4j, Chroma, Ollama, passwords).
- **Per-service** `.env` / `.env.example` — service-specific overrides; referenced by Compose `env_file` where needed.
- **Unified API** `unified_api/.env.example` — unified-server settings only.

## Deferred: Option B (`packages/` + unified env)

Not chosen now. Documented for a future cleanup pass.

### Proposed shape

```
common/
├── packages/
│   ├── llm-service/
│   ├── doc_processing/
│   └── …
├── unified_api/
├── .env                         # Single source of truth for all services
└── docker-compose.yml
```

### Benefits

- Clear monorepo structure; service code grouped under one parent.
- One env file to edit; fewer per-service `.env` templates to maintain.
- Easier onboarding: “all libraries live under `packages/`”.

### Cost of switching later

| Area | Files / settings to update |
|------|----------------------------|
| `unified_api/pyproject.toml` | `[tool.uv.sources]` path deps |
| `unified_api/uv.lock` | Regenerate after path changes |
| `unified_api/Dockerfile.compose` | `COPY` paths |
| `docker-compose.yml` / `docker-compose-test.yaml` | `context`, `env_file`, volume mounts |
| `.gitignore` | Per-service env and log paths |
| `scripts/sync_service_env_from_root.py` | May become unnecessary or simplified |
| `docs/` | Path references in runbooks and service READMEs |
| CI / local dev docs | Clone paths, `cd` instructions |

Optional follow-ups in the same pass: rename `temporial_*` → `temporal_*` (directory names only; API prefixes can stay unchanged).

## When to revisit

Re-evaluate Option B when **all** of the following are true:

1. Unified API is the only entry point for merged services (no workflows depending on standalone per-service Docker images).
2. `fin_rag` integration and env wiring are settled.
3. No open large refactors in flight (e.g. Phase 2 LLM in-process, traversal rename).
4. Team agrees a one-time path migration is cheaper than continued dual conventions.

## Related docs

- [README.md](./README.md) — documentation index
- [compose-runbook.md](./compose-runbook.md) — Docker Compose operations
- [unified-api/migration-notes.md](./unified-api/migration-notes.md) — URL and route migration for API clients
- [unified-api-implementation-plan.md](./unified-api-implementation-plan.md) — merge implementation history
