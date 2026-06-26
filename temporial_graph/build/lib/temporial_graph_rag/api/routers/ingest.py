from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from temporial_graph_rag.api.constants import ONTOLOGIES_DIR
from temporial_graph_rag.api.dependencies import get_chunk_processor, get_neo4j_store
from temporial_graph_rag.api.registry_holder import registry
from temporial_graph_rag.models.ingest import (
    IngestBatchRequest,
    IngestBatchResponse,
    IngestProcessResponse,
    ProcessedChunkSummary,
)
from temporial_graph_rag.ontology.loader import load_ontology
from temporial_graph_rag.pipeline import ChunkProcessor
from neo4j.exceptions import Neo4jError

from fastapi import APIRouter

router = APIRouter()

@router.post("/v1/ingest/chunks", response_model=IngestBatchResponse)
async def ingest_chunks(body: IngestBatchRequest) -> IngestBatchResponse:
    try:
        registry.ensure_binding(body.collection_name, body.ontology_id)
        ontology = load_ontology(ONTOLOGIES_DIR, body.ontology_id)
        for chunk in body.chunks:
            ontology.validate_pair(chunk.canonical_event, chunk.canonical_subevent)
            _ = chunk.extraction_text
        return IngestBatchResponse(
            collection_name=body.collection_name,
            ontology_id=body.ontology_id,
            accepted_chunks=len(body.chunks),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/v1/ingest/chunks/process", response_model=IngestProcessResponse)
async def ingest_and_process_chunks(
    request: Request,
    body: IngestBatchRequest,
    processor: ChunkProcessor = Depends(get_chunk_processor),
) -> IngestProcessResponse:
    try:
        registry.ensure_binding(body.collection_name, body.ontology_id)
        ontology = load_ontology(ONTOLOGIES_DIR, body.ontology_id)
        store = get_neo4j_store(request)
        persisted = 0

        processed: list[ProcessedChunkSummary] = []
        for chunk in body.chunks:
            ontology.validate_pair(chunk.canonical_event, chunk.canonical_subevent)
            result = processor.process_chunk(chunk, ontology=ontology)
            if store is not None:
                try:
                    store.persist_chunk_snapshot(
                        collection_name=body.collection_name,
                        ontology_id=ontology.ontology_id,
                        ontology_version=ontology.ontology_version,
                        chunk=chunk,
                        result=result,
                        snapshot_embed_publish_window_hours=ontology.get_snapshot_embedding_publish_window_hours(
                            chunk.canonical_event
                        ),
                    )
                except Neo4jError as exc:
                    raise HTTPException(status_code=502, detail=f"Neo4j write failed: {exc}") from exc
                persisted += 1
            processed.append(
                ProcessedChunkSummary(
                    chunk_id=result.chunk_id,
                    canonical_event=result.canonical_event,
                    canonical_subevent=result.canonical_subevent,
                    extraction_text=result.extraction_text,
                    embedding_model=result.embedding_model,
                    embedding_vector_size=result.embedding_vector_size,
                    impact_direction=result.impact_direction,
                    impact_magnitude=result.impact_magnitude,
                    impact_probability=result.impact_probability,
                    short_term_return_bps=result.short_term_return_bps,
                    medium_term_return_bps=result.medium_term_return_bps,
                    decay_half_life_days=result.decay_half_life_days,
                    causality_target=result.causality_target,
                    causality_reason=result.causality_reason,
                    entities=result.entities,
                    extracted_events=result.extracted_events,
                )
            )

        return IngestProcessResponse(
            collection_name=body.collection_name,
            ontology_id=body.ontology_id,
            accepted_chunks=len(body.chunks),
            processed=processed,
            persisted_snapshots=persisted,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
