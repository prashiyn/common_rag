---
name: raqe-fastapi-uv
description: Implements and maintains a Reference-Aware Query Engine as a FastAPI server with collection-aware temporal graph traversal. Use when building query parsing/planning/execution, Neo4j graph access, FastAPI endpoints, uv-based dependency management, config.py configuration, and .env.example environment variable documentation.
---

# RAQE FastAPI + uv Skill

## Purpose

Use this skill to implement or extend a production-oriented Reference-Aware Query Engine (RAQE) that supports:

- Collection-scoped multi-document reasoning
- Temporal filtering (quarterly/yearly)
- Cross-reference traversal across sections, tables, and appendices
- Structure-aware context assembly for LLM answering

## Required Project Conventions

1. Treat the application as a FastAPI server.
2. Use `uv` for package and project management.
3. Use `config.py` as the centralized configuration module.
4. Keep a `.env.example` file updated with all required env variables.

## RAQE Domain Model

### Core entities

- `Collection` groups related documents (example: RELIANCE, INFY)
- `Document` stores filing/report metadata
- `Section`, `Table`, `Appendix` capture structure
- Optional analysis nodes: `Event`, `Impact`

### Required temporal document fields

- `period`
- `fiscal_year`
- `timestamp`

## Graph Schema Expectations (Neo4j)

### Nodes

- `(:Collection {id, name})`
- `(:Document {id, name, type, period, fiscal_year, timestamp, created_at})`
- `(:Section {id, title, level})`
- `(:Table {id, label})`
- `(:Appendix {id, label})`
- `(:Event {id, type, subtype, timestamp})`
- `(:Impact {id, score})`

### Relationships

- `(Collection)-[:HAS_DOCUMENT]->(Document)`
- `(Document)-[:HAS_SECTION]->(Section)`
- `(Section)-[:CONTAINS]->(Table)`
- `(Section)-[:REFERS_TO]->(Table|Appendix)`
- `(Event)-[:MENTIONED_IN]->(Section)`
- `(Event)-[:HAS_IMPACT]->(Impact)`

## Application Structure (Target)

Use modules equivalent to:

- `app/agent/query_engine.py`
- `app/agent/parser.py`
- `app/agent/planner.py`
- `app/agent/executor.py`
- `app/agent/context_builder.py`
- `app/agent/answer_generator.py`
- `app/graph/queries.py`
- `app/graph/neo4j_client.py`
- `app/structure/resolver.py`

## Query Lifecycle (Must Preserve)

1. Parse query intent, collection, time range, target.
2. Filter documents by collection + time constraints.
3. Build execution plan from parsed intent.
4. Execute graph traversal with collection scoping.
5. Expand references (`REFERS_TO`) where needed.
6. Build structured context from events/references/tables.
7. Generate final answer from question + context.

## FastAPI Integration Guidance

- Expose a query endpoint (for example, `POST /query/ask`).
- Keep endpoint thin: orchestrate via query engine service function.
- Use typed request/response models where practical.
- Keep parser/planner/executor logic out of the route handler.

## Configuration Workflow

When adding any runtime configuration:

1. Add the variable to `config.py` (with parsing/validation/defaulting rules).
2. Add the variable name and placeholder value to `.env.example`.
3. Ensure code reads configuration from `config.py`, not ad-hoc `os.getenv` calls scattered across modules.

## Execution Checklist

- [ ] Is the flow collection-aware?
- [ ] Is temporal filtering implemented or preserved?
- [ ] Are graph traversals aligned to the RAQE schema?
- [ ] Is FastAPI endpoint logic thin and service-oriented?
- [ ] Are `config.py` and `.env.example` updated together?
- [ ] Is tooling/dependency guidance consistent with `uv`?
