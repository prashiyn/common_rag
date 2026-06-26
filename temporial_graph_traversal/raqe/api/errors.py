from fastapi import HTTPException

from raqe.collection_namespace import to_external


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": {"code": code, "message": message}})


def invalid_query_error(message: str = "Query is invalid.") -> HTTPException:
    return api_error(422, "invalid_query", message)


def missing_collection_error() -> HTTPException:
    return api_error(400, "missing_collection", "Collection is required or must be resolvable from query.")


def no_documents_error() -> HTTPException:
    return api_error(404, "no_documents_in_time_range", "No documents found for the resolved time scope.")


def unresolved_reference_error() -> HTTPException:
    return api_error(422, "unresolved_reference", "One or more references could not be resolved.")


def collection_not_found_error(collection_id: str) -> HTTPException:
    external = to_external(collection_id) or collection_id
    return api_error(404, "collection_not_found", f"Collection '{external}' was not found.")
