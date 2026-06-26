from fastapi import APIRouter

from raqe.agent.query_engine import run_query
from raqe.api.errors import (
    invalid_query_error,
    missing_collection_error,
    no_documents_error,
    unresolved_reference_error,
)
from raqe.models.query_request import QueryRequest
from raqe.models.query_response import QueryResult

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/ask", response_model=QueryResult)
def ask(payload: QueryRequest) -> dict:
    if not payload.question.strip():
        raise invalid_query_error("question must not be empty")

    try:
        result = run_query(
            question=payload.question,
            collection=payload.collection,
            section_hint=payload.section_hint,
        )
    except ValueError as exc:
        message = str(exc).lower()
        if "collection is required" in message:
            raise missing_collection_error() from exc
        raise invalid_query_error(str(exc)) from exc

    if not result.get("execution", {}).get("documents"):
        raise no_documents_error()

    unresolved = [
        ref
        for ref in result.get("execution", {}).get("references", [])
        if ref.get("reference_text") and not ref.get("resolved", True)
    ]
    if payload.strict_reference_resolution and unresolved:
        raise unresolved_reference_error()

    return result
