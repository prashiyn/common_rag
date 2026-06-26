# Common Services

Documentation for the unified Docker Compose stack and APIs lives under **[docs/README.md](docs/README.md)**.

Quick start:

```bash
cp .env.example .env
docker compose --env-file .env up -d unified_api
curl http://127.0.0.1:8000/health
```

See [docs/compose-runbook.md](docs/compose-runbook.md) for full operational guidance.
