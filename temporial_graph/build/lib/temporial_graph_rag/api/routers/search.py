from __future__ import annotations

from typing import Literal

from fastapi import Depends, HTTPException, Request
from neo4j.exceptions import Neo4jError

from temporial_graph_rag.api.constants import ONTOLOGIES_DIR
from temporial_graph_rag.api.dependencies import get_llm_client, require_neo4j_store
from temporial_graph_rag.api.registry_holder import registry
from temporial_graph_rag.graph import Neo4jGraphStore
from temporial_graph_rag.llm import LLMClient
from temporial_graph_rag.models.query import (
    ChunkTimelineItem,
    ChunkTimelineResponse,
    CreateEventSupersessionRequest,
    EventSearchHit,
    EventSearchResponse,
    EventSupersessionCreatedResponse,
    EventSupersessionDetailResponse,
    ImpactPriorResponse,
    MultiStepRagRequest,
    MultiStepRagResponse,
    RagAnswerRequest,
    RagAnswerResponse,
    RagSourceRef,
    SnapshotSearchHit,
    SnapshotSearchResponse,
)
from temporial_graph_rag.ontology.loader import load_ontology
from temporial_graph_rag.retrieval import decay as retrieval_decay
from temporial_graph_rag.retrieval.multi_step import MultiStepRetriever

from fastapi import APIRouter

router = APIRouter()

@router.get("/v1/collections/{collection_name}/impact-prior", response_model=ImpactPriorResponse)
async def impact_prior_preview(
    collection_name: str,
    canonical_event: str,
    canonical_subevent: str,
) -> ImpactPriorResponse:
    binding = registry.get(collection_name)
    if binding is None:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' does not exist")
    try:
        ontology = load_ontology(ONTOLOGIES_DIR, binding.ontology_id)
        ontology.validate_pair(canonical_event, canonical_subevent)
        prior = ontology.get_impact_prior(canonical_event, canonical_subevent)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ImpactPriorResponse(
        collection_name=collection_name,
        ontology_id=ontology.ontology_id,
        ontology_version=ontology.ontology_version,
        canonical_event=canonical_event,
        canonical_subevent=canonical_subevent,
        prior=prior,
    )


@router.get("/v1/collections/{collection_name}/snapshots/search", response_model=SnapshotSearchResponse)
async def search_snapshots(
    request: Request,
    collection_name: str,
    q: str,
    limit: int = 10,
    canonical_event: str | None = None,
    mode: Literal["lexical", "vector"] = "lexical",
    llm: LLMClient = Depends(get_llm_client),
) -> SnapshotSearchResponse:
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter q must not be empty")
    if registry.get(collection_name) is None:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' does not exist")
    store = require_neo4j_store(request)
    limit = min(max(limit, 1), 50)

    query_embedding: list[float] | None = None
    if mode == "vector":
        try:
            emb_resp = llm.embeddings(
                task_name="embeddings",
                input_value=q.strip(),
                input_type="search_query",
            )
            data = emb_resp.get("data") or []
            vec = data[0].get("embedding") if data else None
            if isinstance(vec, list) and vec and all(isinstance(x, (int, float)) for x in vec):
                query_embedding = [float(x) for x in vec]
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Embedding query failed: {exc}") from exc
        if not query_embedding:
            raise HTTPException(
                status_code=502,
                detail="LLM embeddings response did not include a numeric vector for the query.",
            )

    try:
        raw_hits = store.search_snapshots(
            collection_name=collection_name,
            query=q,
            limit=limit,
            canonical_event=canonical_event,
            query_embedding=query_embedding,
        )
    except Neo4jError as exc:
        raise HTTPException(status_code=502, detail=f"Neo4j query failed: {exc}") from exc
    hits = [SnapshotSearchHit(**h) for h in raw_hits]
    return SnapshotSearchResponse(
        collection_name=collection_name,
        query=q.strip(),
        mode=mode,
        hits=hits,
    )


@router.get("/v1/collections/{collection_name}/chunks/{chunk_id}/timeline", response_model=ChunkTimelineResponse)
async def chunk_timeline(
    request: Request,
    collection_name: str,
    chunk_id: str,
    limit: int = 50,
) -> ChunkTimelineResponse:
    if registry.get(collection_name) is None:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' does not exist")
    store = require_neo4j_store(request)
    limit = min(max(limit, 1), 200)
    try:
        raw_items = store.chunk_timeline(
            collection_name=collection_name,
            chunk_id=chunk_id,
            limit=limit,
        )
    except Neo4jError as exc:
        raise HTTPException(status_code=502, detail=f"Neo4j query failed: {exc}") from exc
    items = [ChunkTimelineItem(**r) for r in raw_items]
    return ChunkTimelineResponse(collection_name=collection_name, chunk_id=chunk_id, items=items)


@router.get("/v1/collections/{collection_name}/events/search", response_model=EventSearchResponse)
async def search_events(
    request: Request,
    collection_name: str,
    limit: int = 20,
    canonical_event: str | None = None,
    canonical_subevent: str | None = None,
    q: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    include_superseded: bool = False,
    exclude_decay_suppressed_snapshots: bool = True,
) -> EventSearchResponse:
    if registry.get(collection_name) is None:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' does not exist")
    store = require_neo4j_store(request)
    limit = min(max(limit, 1), 100)
    try:
        rows = store.search_events(
            collection_name=collection_name,
            limit=limit,
            canonical_event=canonical_event,
            canonical_subevent=canonical_subevent,
            query=q,
            start_time=start_time,
            end_time=end_time,
            include_superseded=include_superseded,
            exclude_decay_suppressed_snapshots=exclude_decay_suppressed_snapshots,
        )
    except Neo4jError as exc:
        raise HTTPException(status_code=502, detail=f"Neo4j query failed: {exc}") from exc
    return EventSearchResponse(
        collection_name=collection_name,
        hits=[EventSearchHit(**r) for r in rows],
    )


@router.post(
    "/v1/collections/{collection_name}/events/supersession",
    response_model=EventSupersessionCreatedResponse,
)
async def create_event_supersession(
    collection_name: str,
    body: CreateEventSupersessionRequest,
    request: Request,
) -> EventSupersessionCreatedResponse:
    if registry.get(collection_name) is None:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' does not exist")
    store = require_neo4j_store(request)
    if body.newer_event_id == body.older_event_id:
        raise HTTPException(status_code=400, detail="newer_event_id and older_event_id must differ")
    try:
        row = store.merge_event_supersession(
            collection_name=collection_name,
            newer_event_id=body.newer_event_id,
            older_event_id=body.older_event_id,
            reason=body.reason,
        )
    except Neo4jError as exc:
        raise HTTPException(status_code=502, detail=f"Neo4j query failed: {exc}") from exc
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="One or both events were not found in this collection",
        )
    return EventSupersessionCreatedResponse(collection_name=collection_name, **row)


@router.get(
    "/v1/collections/{collection_name}/events/{event_id}/supersession",
    response_model=EventSupersessionDetailResponse,
)
async def get_event_supersession(
    collection_name: str,
    event_id: str,
    request: Request,
) -> EventSupersessionDetailResponse:
    if registry.get(collection_name) is None:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' does not exist")
    store = require_neo4j_store(request)
    try:
        detail = store.event_supersession_detail(collection_name=collection_name, event_id=event_id)
    except Neo4jError as exc:
        raise HTTPException(status_code=502, detail=f"Neo4j query failed: {exc}") from exc
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found in this collection")
    return EventSupersessionDetailResponse(collection_name=collection_name, **detail)


@router.post("/v1/collections/{collection_name}/rag/answer", response_model=RagAnswerResponse)
async def rag_answer(
    collection_name: str,
    body: RagAnswerRequest,
    request: Request,
    llm: LLMClient = Depends(get_llm_client),
) -> RagAnswerResponse:
    binding = registry.get(collection_name)
    if binding is None:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' does not exist")
    store = require_neo4j_store(request)
    try:
        ontology = load_ontology(ONTOLOGIES_DIR, binding.ontology_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    query_embedding: list[float] | None = None
    if body.retrieval_mode == "vector":
        try:
            emb_resp = llm.embeddings(
                task_name="embeddings",
                input_value=body.question.strip(),
                input_type="search_query",
            )
            data = emb_resp.get("data") or []
            vec = data[0].get("embedding") if data else None
            if isinstance(vec, list) and vec and all(isinstance(x, (int, float)) for x in vec):
                query_embedding = [float(x) for x in vec]
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Embedding query failed: {exc}") from exc
        if not query_embedding:
            raise HTTPException(
                status_code=502,
                detail="LLM embeddings response did not include a numeric vector for the question.",
            )

    fetch_limit = min(max(body.top_k * 5, body.top_k), 60)
    try:
        raw_hits = store.search_snapshots(
            collection_name=collection_name,
            query=body.question,
            limit=fetch_limit,
            query_embedding=query_embedding,
        )
    except Neo4jError as exc:
        raise HTTPException(status_code=502, detail=f"Neo4j query failed: {exc}") from exc

    ranked = retrieval_decay.sort_snapshot_hits_by_decay_and_similarity(
        retrieval_decay.enrich_snapshot_hits_with_decay(raw_hits, ontology)
    )[: body.top_k]

    if not ranked:
        return RagAnswerResponse(
            collection_name=collection_name,
            question=body.question,
            answer="No chunk snapshots above the ontology decay threshold for this collection.",
            sources=[],
        )

    parts: list[str] = []
    for i, h in enumerate(ranked):
        text = (h.get("extraction_text") or "")[:2000]
        parts.append(
            f"[{i + 1}] snapshot_id={h.get('snapshot_id')} chunk_id={h.get('chunk_id')} "
            f"doc_id={h.get('doc_id')}\n{text}"
        )
    context = "\n\n".join(parts)
    try:
        resp = llm.complete(
            task_name="answer_synthesis",
            messages=[
                {
                    "role": "system",
                    "content": "Answer using only the provided context snippets. If insufficient, say so briefly.",
                },
                {
                    "role": "user",
                    "content": f"Question:\n{body.question}\n\nContext:\n{context}",
                },
            ],
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM answer failed: {exc}") from exc

    answer = str(resp.get("content", "")).strip()
    sources = [
        RagSourceRef(
            snapshot_id=h.get("snapshot_id"),
            chunk_id=h.get("chunk_id"),
            doc_id=h.get("doc_id"),
        )
        for h in ranked
    ]
    return RagAnswerResponse(
        collection_name=collection_name,
        question=body.question,
        answer=answer or "(empty model response)",
        sources=sources,
    )


@router.post(
    "/v1/collections/{collection_name}/rag/multi_step",
    response_model=MultiStepRagResponse,
)
async def rag_multi_step(
    collection_name: str,
    body: MultiStepRagRequest,
    request: Request,
    llm: LLMClient = Depends(get_llm_client),
) -> MultiStepRagResponse:
    binding = registry.get(collection_name)
    if binding is None:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' does not exist")
    store = require_neo4j_store(request)
    try:
        ontology = load_ontology(ONTOLOGIES_DIR, binding.ontology_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    retriever = MultiStepRetriever(
        llm=llm,
        store=store,
        ontology=ontology,
        collection_name=collection_name,
        max_steps=body.max_steps,
    )
    try:
        result = retriever.run(body.question)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Multi-step retrieval failed: {exc}") from exc
    return MultiStepRagResponse(
        collection_name=collection_name,
        question=body.question,
        initial_plan=result.initial_plan,
        answer=result.answer,
        steps=result.steps,
    )


