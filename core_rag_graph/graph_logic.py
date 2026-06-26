import asyncio
import copy
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List

from fastapi import WebSocket

from graph.config import get_config, prompt_templates
from graph.utils import kt_gen as constructor
from graph.utils import call_llm_api
from graph.utils import graph_processor
from graph.utils.collection_id_scope import to_external_collection_id, to_internal_collection_id
from graph.utils.logger import logger

from schemas import (
    ChunkInput,
    CollectionMetadata,
    CollectionResponse,
    CollectionListResponse,
    ExtracGraphDataResponse,
    GetCollectionByIdRequest,
    GetOrCreateCollectionRequest,
    IngestChunksRequest,
)
from state import CONFIG, GRAPH_REPOSITORY, RUNTIME_METRICS

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)


manager = ConnectionManager()


COLLECTIONS_REGISTRY_PATH = "./data/collections/collections.json"


def _ensure_collections_registry() -> None:
    os.makedirs(os.path.dirname(COLLECTIONS_REGISTRY_PATH), exist_ok=True)
    if not os.path.exists(COLLECTIONS_REGISTRY_PATH):
        with open(COLLECTIONS_REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def _load_collections_registry() -> List[Dict[str, Any]]:
    _ensure_collections_registry()
    with open(COLLECTIONS_REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("collection_id"), str):
            row = dict(item)
            row["collection_id"] = to_internal_collection_id(row["collection_id"])
            normalized.append(row)
        elif isinstance(item, dict):
            normalized.append(item)
    return normalized


def _save_collections_registry(collections: List[Dict[str, Any]]) -> None:
    _ensure_collections_registry()
    with open(COLLECTIONS_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(collections, f, ensure_ascii=False, indent=2)


def _normalize_chunk(chunk: Dict[str, Any], file_name: str) -> Dict[str, Any]:
    """Normalize incoming chunk payload to internal structure.

    Canonical external schema:
    - chunk_id, content, type, doc_id, page, bundle_id, section_title, title_summary,
      publish_date, prev_chunk, next_chunk

    Internal fields used by existing graph pipeline:
    - section_title, content, meta_data
    """
    if not isinstance(chunk, dict):
        raise ValueError("Each chunk must be a JSON object")

    chunk_type = str(chunk.get("type", "text")).lower()
    content = chunk.get("content", "")
    title_summary = chunk.get("title_summary", "") or ""

    # For image chunks, use title_summary as textual representation.
    if chunk_type == "image":
        content = title_summary

    if content is None:
        content = ""
    if not isinstance(content, str):
        content = str(content)

    section_title = chunk.get("section_title") or file_name.split(".")[0]
    if not isinstance(section_title, str):
        section_title = str(section_title)

    normalized = {
        "section_title": section_title,
        "content": content,
        "meta_data": {
            "chunk_id": chunk.get("chunk_id"),
            "type": chunk_type,
            "doc_id": chunk.get("doc_id"),
            "page": chunk.get("page"),
            "bundle_id": chunk.get("bundle_id"),
            "section_title": chunk.get("section_title"),
            "title_summary": title_summary,
            "publish_date": chunk.get("publish_date"),
            "prev_chunk": chunk.get("prev_chunk"),
            "next_chunk": chunk.get("next_chunk"),
        },
    }
    return normalized


def _build_graph_from_chunks(payload: IngestChunksRequest) -> ExtracGraphDataResponse:
    """Shared ingestion logic for chunk payloads."""
    ingest_start = time.perf_counter()
    chunks = payload.chunks
    collection_id = _resolve_collection_id(payload.collection_id)
    file_name = payload.file_name
    temperature = payload.temperature
    schema = payload.schema

    normalized_chunks = [_normalize_chunk(chunk.model_dump(), file_name) for chunk in chunks]

    config = get_config()
    config.construction.mode = "general"  # "agent"
    dataset = "demo"
    dataset_config = config.get_dataset_config(dataset)
    dataset_config.corpus_path = "data/demo/custom_corpus.json"
    dataset_config.schema_path = "schemas/custom.json"
    dataset_config.graph_output = "output/graphs/custom_new.json"
    if schema:
        config.prompts["construction"]["general"] = prompt_templates.construction_prompt_with_schema
        config.prompts["construction"]["general_eng"] = prompt_templates.construction_prompt_with_schema_eng
    else:  # No schema: use generic templates
        config.prompts["construction"]["general"] = prompt_templates.construction_prompt_flexible
        config.prompts["construction"]["general_eng"] = prompt_templates.construction_prompt_flexible_eng
    config.construction.TEMPERATURE = temperature
    embedding_model = None
    builder = constructor.KTBuilder(
        dataset,
        embedding_model,
        dataset_config.schema_path,
        schema=schema,
        mode=config.construction.mode,
        config=config
    )
    res_data = builder.build_knowledge_graph(file_name, normalized_chunks)

    # =========== update graph ============
    GRAPH_REPOSITORY.merge_relationships(collection_id, file_name, res_data, config)

    # =========== build graph_vocabulary_set ============
    graph_vocabulary_set = set()
    for node in builder.graph.nodes:
        node_json = builder.graph.nodes[node]
        if node_json['properties'].get('schema_type'):
            schema_type = f"K:{node_json['properties'].get('schema_type')}"
        else:
            schema_type = "K:graph_node"
        node_msg = f"{node_json['properties']['name']}|||schema_type:{schema_type}"
        graph_vocabulary_set.add(node_msg)

    # =========== build graph_chunks ============
    graph_chunks = []
    for triple in res_data:
        reference_chunk_id = triple["start_node"]["properties"]["chunk id"]
        meta_data = builder.all_chunks[reference_chunk_id].get("meta_data", {})
        meta_data["reference_content"] = builder.all_chunks[reference_chunk_id].get("content", "")
        temp_triple = copy.deepcopy(triple)
        if 'chunk id' in temp_triple['start_node']['properties']:
            del temp_triple['start_node']['properties']['chunk id']
        if 'chunk id' in temp_triple['end_node']['properties']:
            del temp_triple['end_node']['properties']['chunk id']
        graph_data_text = (
            f"{triple['start_node']['properties']['name']} "
            f"{triple['relation']} "
            f"{triple['end_node']['properties']['name']}"
        )
        graph_chunks.append(
            {
                "chunk_type": "graph",
                "graph_data_text": graph_data_text,
                "graph_data": copy.deepcopy(temp_triple),
                "meta_data": meta_data,
            }
        )

    response = ExtracGraphDataResponse(
        success=True,
        message="Chunks ingested successfully",
        graph_chunks=graph_chunks,
        graph_vocabulary_set=graph_vocabulary_set,
    )
    elapsed_ms = (time.perf_counter() - ingest_start) * 1000.0
    RUNTIME_METRICS["ingest_latency_ms_total"] += elapsed_ms
    RUNTIME_METRICS["ingest_requests_total"] += 1
    return response


def _resolve_collection_id(collection_id: str) -> str:
    """Validate and normalize collection identifier to internal storage form."""
    if collection_id is None or str(collection_id).strip() == "":
        raise ValueError("collection_id is required")
    return to_internal_collection_id(str(collection_id).strip())


def _query_terms(text: str) -> set:
    return {t.lower() for t in str(text).split() if t.strip()}


def _rank_graph_evidence(graph, query: str, top_k: int) -> List[Dict[str, Any]]:
    terms = _query_terms(query)
    evidence: List[Dict[str, Any]] = []
    if not terms:
        return evidence

    for u, v, data in graph.edges(data=True):
        u_data = graph.nodes[u]
        v_data = graph.nodes[v]
        relation = str(data.get("relation", ""))
        text = f"{u} {relation} {v}"
        score = 0.0
        lower_text = text.lower()
        for t in terms:
            if t in lower_text:
                score += 1.0
        score += float(u_data.get("pagerank", 0.0)) + float(v_data.get("pagerank", 0.0))
        if score <= 0:
            continue
        evidence.append(
            {
                "type": "edge",
                "score": round(score, 6),
                "text": text,
                "source": u,
                "target": v,
                "relation": relation,
                "source_schema_type": u_data.get("properties", {}).get("schema_type", ""),
                "target_schema_type": v_data.get("properties", {}).get("schema_type", ""),
                "source_files": u_data.get("properties", {}).get("file_names", []),
                "target_files": v_data.get("properties", {}).get("file_names", []),
            }
        )

    evidence.sort(key=lambda x: x["score"], reverse=True)
    return evidence[: max(1, top_k)]


def _build_chunk_evidence(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chunk_map: Dict[str, Dict[str, Any]] = {}
    for item in evidence:
        relation_text = item.get("text", "")
        for side in ("source", "target"):
            file_key = f"{side}_files"
            entity_name = str(item.get(side, ""))
            for file_name in item.get(file_key, []) or []:
                chunk_key = f"{file_name}::{entity_name}"
                if chunk_key not in chunk_map:
                    chunk_map[chunk_key] = {
                        "chunk_id": chunk_key,
                        "doc_id": file_name,
                        "entity": entity_name,
                        "evidence_texts": [],
                    }
                if relation_text and relation_text not in chunk_map[chunk_key]["evidence_texts"]:
                    chunk_map[chunk_key]["evidence_texts"].append(relation_text)

    chunk_evidence = list(chunk_map.values())
    chunk_evidence.sort(key=lambda x: len(x["evidence_texts"]), reverse=True)
    return chunk_evidence


def _build_context_from_evidence(evidence: List[Dict[str, Any]]) -> str:
    if not evidence:
        return ""
    lines = []
    for idx, item in enumerate(evidence, 1):
        lines.append(f"{idx}. {item['text']}")
    return "\n".join(lines)


async def send_progress_update(client_id: str, stage: str, progress: int, message: str):
    """Send progress update via WebSocket"""
    await manager.send_message({
        "type": "progress",
        "stage": stage,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }, client_id)

async def send_community_reports(client_id: str, reports: List[Dict], message: str = "community_reports ready"):
    await manager.send_message({
        "type": "community_reports",
        "data": reports,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }, client_id)

async def _generate_community_reports_task(collection_id: str, config, client_id: str):
    try:
        await send_progress_update(client_id, "generate_community_reports", 1, "started")
        reports: List[Dict] = []
        new_graph = GRAPH_REPOSITORY.load_collection_graph(collection_id)
        if new_graph is not None:
            reports = await asyncio.to_thread(graph_processor.extract_community, new_graph, config)
            GRAPH_REPOSITORY.save_community_reports(collection_id, reports)
            await send_progress_update(client_id, "generate_community_reports", 90, "reports generated")
            await send_community_reports(client_id, reports, "completed")
            await send_progress_update(client_id, "generate_community_reports", 100, "completed")
        else:
            await send_progress_update(client_id, "generate_community_reports", 0, "graph not found")
            await send_community_reports(client_id, [], "graph not found")
    except Exception as e:
        await send_progress_update(client_id, "generate_community_reports", 0, f"failed: {str(e)}")
        await manager.send_message({
            "type": "community_reports_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, client_id)

