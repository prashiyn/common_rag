from raqe.agent.planner import build_plan


def test_planner_includes_phase5_execution_flow_steps() -> None:
    plan = build_plan({"intent": "WHY"})
    assert plan["steps"] == [
        "resolve_documents",
        "load_document_chunks",
        "filter_chunks",
        "fetch_events",
        "traverse_references",
        "fetch_tables",
        "build_context",
        "generate_answer",
    ]
