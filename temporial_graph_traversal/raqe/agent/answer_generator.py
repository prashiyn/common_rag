from raqe.models.query_response import QueryAnswer
from raqe.llm.client import completion_via_llm_service


def generate_answer(question: str, context: dict) -> dict:
    summary = context.get("summary", {})
    evidence = context.get("evidence", [])
    references = context.get("reference_traces", [])
    resolved_count = len([item for item in references if item.get("resolved")])
    reference_total = max(int(summary.get("reference_count", 0)), 1)
    confidence = min(1.0, 0.4 + (resolved_count / reference_total) * 0.6)

    supporting_facts = []
    for item in evidence[:2]:
        supporting_facts.append(
            f"{item.get('document_id')}:{item.get('chunk_id')} - {item.get('title_summary')}"
        )
    for ref in references[:2]:
        supporting_facts.append(
            f"ref={ref.get('reference_text')} resolved={ref.get('resolved')}"
        )

    context_summary = (
        f"documents={summary.get('document_count', 0)}, "
        f"chunks={summary.get('chunk_count', 0)}, "
        f"references={summary.get('reference_count', 0)}, "
        f"tables={summary.get('table_count', 0)}"
    )
    fallback_answer = (
        "Generated answer based on scoped context. "
        f"Processed {summary.get('chunk_count', 0)} chunks and {summary.get('reference_count', 0)} references."
    )
    llm_messages = [
        {
            "role": "system",
            "content": (
                "You are a financial QA assistant. "
                "Answer concisely from provided context summary and supporting facts."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question: {question}\n"
                f"Context summary: {context_summary}\n"
                f"Supporting facts: {supporting_facts}"
            ),
        },
    ]
    llm_answer = completion_via_llm_service(use_case="answer_generation", messages=llm_messages)
    direct_answer = llm_answer or fallback_answer

    answer = QueryAnswer(
        question=question,
        direct_answer=direct_answer,
        confidence=round(confidence, 3),
        context_summary=context_summary,
        supporting_facts=supporting_facts,
    )
    return answer.model_dump()
