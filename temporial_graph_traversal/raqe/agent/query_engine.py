from raqe.agent.answer_generator import generate_answer
from raqe.agent.context_builder import build_context
from raqe.agent.executor import execute_plan
from raqe.agent.parser import parse_query
from raqe.agent.planner import build_plan
from raqe.models.query_response import QueryResult
from raqe.observability.logging import elapsed_ms, log_stage, start_timer


def run_query(
    question: str,
    collection: str | None = None,
    section_hint: str | None = None,
) -> dict:
    timer = start_timer()
    parsed = parse_query(question, collection_override=collection, section_hint=section_hint)
    log_stage("parsed_query", {"collection": parsed["collection"], "time_mode": parsed["time_context"]["mode"]})
    plan = build_plan(parsed)
    log_stage("plan_built", {"steps": len(plan.get("steps", []))})
    execution = execute_plan(plan, parsed)
    unresolved_refs = len(
        [ref for ref in execution.get("references", []) if ref.get("reference_text") and not ref.get("resolved", True)]
    )
    log_stage(
        "execution_complete",
        {
            "documents": len(execution.get("documents", [])),
            "chunks": len(execution.get("filtered_chunks", [])),
            "references": len(execution.get("references", [])),
            "unresolved_references": unresolved_refs,
        },
    )
    context = build_context(execution)
    answer = generate_answer(question, context)
    result = QueryResult(
        parsed_query=parsed,
        plan=plan,
        execution=execution,
        context=context,
        answer=answer,
    )
    payload = result.model_dump()
    log_stage("query_complete", {"elapsed_ms": elapsed_ms(timer), "confidence": payload["answer"]["confidence"]})
    return payload
