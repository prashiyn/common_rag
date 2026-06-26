# doc-processing

> **Unified API:** routes are mounted at `/doc-processing` on port **8000** (test: **18000**).  
> Canonical docs: [README.md](./README.md) · [document-chunking.md](./document-chunking.md) · [migration-notes](../../unified-api/migration-notes.md)

Document processing, conversions and chunking for RAG. Uses **docling** (VLM, EasyOCR), **unstructured** (PDF, MD, XLS, PPT, DOC, CSV, images), **ixbrl-parse**, and **markitdown**.

LLM APIs are owned by the standalone `llm-service` and are not exposed from this service.

## Setup

```bash
uv sync
```

## Run

```bash
uv run uvicorn doc_processing.main:app --reload
```
