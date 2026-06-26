def build_plan(parsed_query: dict) -> dict:
    return {
        "steps": [
            "resolve_documents",
            "load_document_chunks",
            "filter_chunks",
            "fetch_events",
            "traverse_references",
            "fetch_tables",
            "build_context",
            "generate_answer",
        ],
        "parsed_query": parsed_query,
    }
