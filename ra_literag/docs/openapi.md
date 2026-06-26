# OpenAPI spec for RAG-Anything API

This folder contains the OpenAPI 3.0 specification for the RAG-Anything FastAPI service so other services can generate clients or validate requests.

## Generated files

- **`openapi.json`** – Full OpenAPI 3.0 schema (JSON).
- **`openapi.yaml`** – Same schema in YAML (requires `pyyaml` when generating).

Regenerate after API changes:

```bash
# From repo root, with server deps installed
uv run python scripts/generate_openapi.py
```

## Using the spec

### When the server is running

- **JSON**: `GET {base_url}/openapi.json`
- **Swagger UI**: `GET {base_url}/docs`
- **ReDoc**: `GET {base_url}/redoc`

### From static files (no server)

Point your client generator or gateway at:

- `docs/openapi.json`, or  
- `docs/openapi.yaml`

Examples:

- **OpenAPI Generator** (e.g. Python client):  
  `npx @openapitools/openapi-generator-cli generate -i docs/openapi.json -g python -o ./client`
- **Postman**: Import → Link → paste URL to `openapi.json` or upload the file.
- **Kubernetes/Ingress**: Use the spec for API documentation or validation.

### Overriding the server URL

The schema uses a single server entry with `url: "/"` (relative). To fix the base URL when importing elsewhere:

1. Edit the generated `openapi.json` / `openapi.yaml` and set `servers[0].url` to your base URL (e.g. `https://api.example.com`), or  
2. Configure your client/gateway to use a base URL when resolving relative paths.

## Tags in the spec

- **health** – `GET /health`, `GET /ready`
- **config** – `GET /config`, `GET /config/{workspace_id}`, `POST /config/{workspace_id}`
- **query** – `POST /query`, `POST /query/multimodal`
- **ingest** – `POST /content/insert`, `POST /documents/process`
