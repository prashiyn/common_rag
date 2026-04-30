---
name: docker-compose-unified
description: Creates and maintains a unified Docker Compose stack for the standalone services core_rag_graph, fin_rag, ra_literag, temporial_graph, temporial_graph_openai, and temporial_graph_traversal with shared databases (chroma server, neo4j, postgres). Use when adding services, changing container ports, wiring environment variables, or updating compose dependencies.
---

# Unified Docker Compose Skill

## Goal

Maintain one compose stack that launches all six services plus shared databases:
- `postgres`
- `neo4j`
- `chroma`

## Service Mapping

Use these service names and default container ports:
- `core_rag_graph` -> `20050`
- `fin_rag` -> `6005`
- `ra_literag` -> `8000`
- `temporial_graph` -> `8082`
- `temporial_graph_openai` -> `8080`
- `temporial_graph_traversal` -> `8090`

## Database Wiring

- **Postgres**
  - Host inside compose network: `postgres`
  - Port: `5432`
  - Default URL format: `postgresql://postgres:postgres@postgres:5432/<db_name>`
- **Neo4j**
  - Host: `neo4j`
  - Bolt URL: `bolt://neo4j:7687`
  - Browser port: `7474`
- **Chroma**
  - Host: `chroma`
  - Internal port: `8000`

## Authoring Rules

1. Keep all services in one root `docker-compose.yml`.
2. Use `depends_on` with health checks for database readiness.
3. Keep persistent named volumes for each database.
4. Prefer explicit environment variables over hidden defaults.
5. If a service has no Dockerfile, add `Dockerfile.compose` in that service directory.
6. Keep compose YAML compatible with Docker Compose v2 (no top-level `version` key required).

## Validation Checklist

- Run `docker compose config` and fix schema issues.
- Confirm no host port conflicts.
- Confirm each service command points to its FastAPI app.
- Confirm all DB hostnames use compose service names (`postgres`, `neo4j`, `chroma`), not `localhost`.
