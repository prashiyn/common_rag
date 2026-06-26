import asyncio
import time

from fastapi import APIRouter, HTTPException

from graph.config import get_config
from graph.utils import call_llm_api
from graph.utils import graph_processor

from graph_logic import (
    _build_chunk_evidence,
    _build_context_from_evidence,
    _build_graph_from_chunks,
    _load_collections_registry,
    _rank_graph_evidence,
    _resolve_collection_id,
    _save_collections_registry,
    _generate_community_reports_task,
    manager,
    send_progress_update,
)
from schemas import (
    CollectionMetadata,
    CollectionResponse,
    CollectionListResponse,
    CollectionScopedRequest,
    CommunityReportsRequest,
    CommunityReportsResponse,
    DeleteFileRequest,
    ExtracGraphDataResponse,
    GetCollectionByIdRequest,
    GetGraphRequest,
    GetOrCreateCollectionRequest,
    GraphDataResponse,
    IngestChunksRequest,
    QueryRequest,
    QueryResponse,
    RequestResponse,
    RetrieveRequest,
    RetrieveResponse,
    TestPostRequest,
)
from state import GRAPH_REPOSITORY, RUNTIME_METRICS

router = APIRouter()

@router.post("/api/extrac_graph_data", response_model=ExtracGraphDataResponse)
async def extrac_graph_data(payload: IngestChunksRequest):
    """Legacy route: ingest chunk list and build/merge graph."""
    try:
        return _build_graph_from_chunks(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/ingest_chunks", response_model=ExtracGraphDataResponse)
async def ingest_chunks(payload: IngestChunksRequest):
    """Canonical chunk ingestion endpoint for Graph RAG construction."""
    try:
        return _build_graph_from_chunks(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/api/generate_community_reports", response_model=CommunityReportsResponse)
async def generate_community_reports(payload: CommunityReportsRequest):
    """extrac_graph_data endpoint  chunks: List[Dict], client_id: str = 'default' """
    try:
        collection_id = _resolve_collection_id(payload.collection_id)
        client_id = payload.client_id
        logger.info(f"generate_community_reports, collection_id: {collection_id}")
        config = get_config()
        config.construction.mode = "general"  # "agent"

        asyncio.create_task(_generate_community_reports_task(collection_id, config, client_id))

        return CommunityReportsResponse(
            success=True,
            message="generate_community_reports started",
            community_reports=[],
        )

    except Exception as e:
        await send_progress_update(client_id, "generate_community_reports", 0, f"failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/get_community_reports", response_model=CommunityReportsResponse)
async def get_community_reports(payload: CollectionScopedRequest):
    try:
        collection_id = _resolve_collection_id(payload.collection_id)
        client_id = payload.client_id
        reports = GRAPH_REPOSITORY.load_community_reports(collection_id)
        if reports is None:
            return CommunityReportsResponse(
                success=True,
                message="not ready",
                community_reports=[],
            )
        await send_progress_update(client_id, "get_community_reports", 10, "get_community_reports completed successfully!")
        return CommunityReportsResponse(
            success=True,
            message="ok",
            community_reports=reports,
        )
    except Exception as e:
        await send_progress_update(client_id, "get_community_reports", 0, f"failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/delete_file", response_model=ExtracGraphDataResponse)
async def delete_file(payload: DeleteFileRequest):
    """update graph """
    try:
        collection_id = _resolve_collection_id(payload.collection_id)
        file_name = payload.file_name
        client_id = payload.client_id

        # =========== update graph ============
        GRAPH_REPOSITORY.delete_file(collection_id, file_name)
        await send_progress_update(client_id, "delete_file", 10, "delete_file completed successfully!")

        return RequestResponse(
            success=True,
            message="Files deleted successfully",
        )

    except Exception as e:
        await send_progress_update(client_id, "delete_file", 0, f"deleted failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/delete_collection", response_model=ExtracGraphDataResponse)
async def delete_collection(payload: CollectionScopedRequest):
    """delete collection graph"""
    try:
        collection_id = _resolve_collection_id(payload.collection_id)
        client_id = payload.client_id

        # =========== update graph ============
        GRAPH_REPOSITORY.delete_collection(collection_id)
        collections = _load_collections_registry()
        collections = [c for c in collections if c.get("collection_id") != collection_id]
        _save_collections_registry(collections)
        await send_progress_update(client_id, "delete_collection", 10, "delete_collection completed successfully!")

        return RequestResponse(
            success=True,
            message="delete_collection successfully",
        )

    except Exception as e:
        await send_progress_update(client_id, "delete_collection", 0, f"deleted failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/collections/{collection_id}", response_model=RequestResponse)
async def delete_collection_rest(collection_id: str):
    """Canonical REST endpoint: delete collection by id."""
    return await delete_collection(CollectionScopedRequest(collection_id=collection_id, client_id="default"))


@router.post("/api/delete_kb", response_model=ExtracGraphDataResponse)
async def delete_kb(payload: CollectionScopedRequest):
    """Legacy alias for delete_collection."""
    return await delete_collection(payload)


@router.post("/api/test_post")
async def test_post(payload: TestPostRequest):
    """test post"""
    time.sleep(6)
    return {
        "code": 0,
        "success": True,
        "message": f"test: {payload.payload} successfully",
    }


@router.post("/api/get_kb_graph_data", response_model=GraphDataResponse)
async def get_kb_graph_data(payload: GetGraphRequest):
    """get graph data"""
    query_start = time.perf_counter()
    try:
        collection_id = _resolve_collection_id(payload.collection_id)
        client_id = payload.client_id

        graph_data = {
            "graph": {
                "directed": False,
                "multigraph": False,
                "nodes": [],
                "edges": []
            }
        }

        graph = GRAPH_REPOSITORY.load_collection_graph(collection_id)
        if graph is not None:
            for node in graph.nodes(data=True):
                if node[1]["label"] == "entity":
                    graph_data["graph"]["nodes"].append({
                        "entity_name": node[0],
                        "entity_type": node[1]["label"],
                        "description": "",
                        "source_id": node[1]["properties"]["file_names"]
                    })
            for edge in graph.edges(data=True):
                if edge[2]["relation"] != "has_attribute":
                    graph_data["graph"]["edges"].append({
                        "source_entity": edge[0],
                        "target_entity": edge[1],
                        "description": edge[2]["relation"],
                        "weight": 1.0,
                    })

        await send_progress_update(client_id, "get_kb_graph_data", 10, "get_kb_graph_data completed successfully!")

        response = GraphDataResponse(
            success=True,
            message="get_kb_graph_data successfully",
            graph_data=graph_data
        )
        elapsed_ms = (time.perf_counter() - query_start) * 1000.0
        RUNTIME_METRICS["query_latency_ms_total"] += elapsed_ms
        RUNTIME_METRICS["query_requests_total"] += 1
        return response

    except Exception as e:
        await send_progress_update(client_id, "get_kb_graph_data", 0, f"deleted failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/retrieve", response_model=RetrieveResponse)
async def retrieve(payload: RetrieveRequest):
    query_start = time.perf_counter()
    try:
        collection_id = _resolve_collection_id(payload.collection_id)
        graph = GRAPH_REPOSITORY.load_collection_graph(collection_id)
        if graph is None:
            return RetrieveResponse(
                success=True,
                message="collection graph not found",
                query=payload.query,
                collection_id=collection_id,
                evidence=[],
                chunk_evidence=[],
            )

        evidence = _rank_graph_evidence(graph, payload.query, payload.top_k)
        chunk_evidence = _build_chunk_evidence(evidence)
        elapsed_ms = (time.perf_counter() - query_start) * 1000.0
        RUNTIME_METRICS["query_latency_ms_total"] += elapsed_ms
        RUNTIME_METRICS["query_requests_total"] += 1

        return RetrieveResponse(
            success=True,
            message="retrieve success",
            query=payload.query,
            collection_id=collection_id,
            evidence=evidence,
            chunk_evidence=chunk_evidence,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/query", response_model=QueryResponse)
async def query(payload: QueryRequest):
    query_start = time.perf_counter()
    try:
        collection_id = _resolve_collection_id(payload.collection_id)
        graph = GRAPH_REPOSITORY.load_collection_graph(collection_id)
        if graph is None:
            return QueryResponse(
                success=True,
                message="collection graph not found",
                question=payload.question,
                collection_id=collection_id,
                answer="No graph found for this collection.",
                evidence=[],
                chunk_evidence=[],
            )

        evidence = _rank_graph_evidence(graph, payload.question, payload.top_k)
        chunk_evidence = _build_chunk_evidence(evidence)
        context = _build_context_from_evidence(evidence)

        config = get_config()
        prompt = config.get_prompt_formatted(
            "retrieval",
            "general",
            question=payload.question,
            context=context,
        )
        llm = call_llm_api.LLMCompletionCall(
            temperature=payload.temperature,
            use_case="query_answering",
        )
        answer = llm.call_api(prompt).strip()
        if not answer:
            answer = "No answer generated."

        elapsed_ms = (time.perf_counter() - query_start) * 1000.0
        RUNTIME_METRICS["query_latency_ms_total"] += elapsed_ms
        RUNTIME_METRICS["query_requests_total"] += 1

        return QueryResponse(
            success=True,
            message="query success",
            question=payload.question,
            collection_id=collection_id,
            answer=answer,
            evidence=evidence,
            chunk_evidence=chunk_evidence,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/get-or-create-collection", response_model=CollectionResponse)
async def get_or_create_collection(payload: GetOrCreateCollectionRequest):
    try:
        collection_id = payload.collection_id.strip()
        if not collection_id:
            raise HTTPException(status_code=400, detail="collection_id cannot be empty")
        now = datetime.now().isoformat()
        collections = _load_collections_registry()
        existing = next((c for c in collections if c.get("collection_id") == collection_id), None)
        if existing:
            existing["updated_at"] = now
            if payload.name:
                existing["name"] = payload.name
            if payload.description is not None:
                existing["description"] = payload.description
            _save_collections_registry(collections)
            return CollectionResponse(
                success=True,
                message="collection fetched",
                collection=CollectionMetadata(**existing),
            )

        new_obj = {
            "collection_id": collection_id,
            "name": payload.name or to_external_collection_id(collection_id),
            "description": payload.description or "",
            "created_at": now,
            "updated_at": now,
        }
        collections.append(new_obj)
        _save_collections_registry(collections)
        return CollectionResponse(
            success=True,
            message="collection created",
            collection=CollectionMetadata(**new_obj),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/get-collection-metadata-by-collection-id", response_model=CollectionResponse)
async def get_collection_metadata_by_collection_id(payload: GetCollectionByIdRequest):
    try:
        collection_id = payload.collection_id.strip()
        collections = _load_collections_registry()
        existing = next((c for c in collections if c.get("collection_id") == collection_id), None)
        if not existing:
            raise HTTPException(status_code=404, detail="collection not found")
        return CollectionResponse(
            success=True,
            message="collection fetched",
            collection=CollectionMetadata(**existing),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/get-all-collections", response_model=CollectionListResponse)
async def get_all_colecctions():
    try:
        collections = _load_collections_registry()
        parsed = [CollectionMetadata(**c) for c in collections]
        return CollectionListResponse(
            success=True,
            message="collections fetched",
            collections=parsed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/collections", response_model=CollectionListResponse)
async def get_all_collections():
    """Canonical endpoint: list all collections."""
    return await get_all_colecctions()


@router.get("/api/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection_metadata(collection_id: str):
    """Canonical endpoint: get collection metadata by id."""
    return await get_collection_metadata_by_collection_id(
        GetCollectionByIdRequest(collection_id=collection_id)
    )


@router.post("/api/collections/get-or-create", response_model=CollectionResponse)
async def get_or_create_collection_canonical(payload: GetOrCreateCollectionRequest):
    """Canonical endpoint: get existing collection or create it."""
    return await get_or_create_collection(payload)


@router.post("/api/collections", response_model=CollectionResponse)
async def create_collection_canonical(payload: GetOrCreateCollectionRequest):
    """Canonical REST endpoint: create collection metadata."""
    return await get_or_create_collection(payload)


@router.get("/api/metrics")
async def get_metrics():
    ingest_avg = (
        RUNTIME_METRICS["ingest_latency_ms_total"] / RUNTIME_METRICS["ingest_requests_total"]
        if RUNTIME_METRICS["ingest_requests_total"] > 0
        else 0.0
    )
    query_avg = (
        RUNTIME_METRICS["query_latency_ms_total"] / RUNTIME_METRICS["query_requests_total"]
        if RUNTIME_METRICS["query_requests_total"] > 0
        else 0.0
    )
    processor_metrics = graph_processor.get_operational_metrics()
    return {
        "ingestion_latency_ms_avg": round(ingest_avg, 3),
        "ingestion_requests_total": RUNTIME_METRICS["ingest_requests_total"],
        "query_latency_ms_avg": round(query_avg, 3),
        "query_requests_total": RUNTIME_METRICS["query_requests_total"],
        "merge_conflicts_total": processor_metrics.get("merge_conflicts_total", 0),
        "failed_resolutions_total": processor_metrics.get("failed_resolutions_total", 0),
    }


@router.post("/api/getOrCreateCollection", response_model=CollectionResponse)
async def get_or_create_collection_legacy(payload: GetOrCreateCollectionRequest):
    """Legacy alias for get-or-create-collection."""
    return await get_or_create_collection(payload)


@router.post("/api/getCollectionMetadataByCollectionId", response_model=CollectionResponse)
async def get_collection_metadata_by_collection_id_legacy(payload: GetCollectionByIdRequest):
    """Legacy alias for get-collection-metadata-by-collection-id."""
    return await get_collection_metadata_by_collection_id(payload)


@router.get("/api/getAllColecctions", response_model=CollectionListResponse)
async def get_all_colecctions_legacy():
    """Legacy alias for get-all-collections."""
    return await get_all_colecctions()


@router.get("/api/test")
async def test():
    """test"""
    return {
        "code": 0,
        "success": True,
        "message": f"test successfully",
    }


