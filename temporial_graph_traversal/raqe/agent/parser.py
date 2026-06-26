import re

from raqe.collection_namespace import to_internal
from raqe.config import get_settings
from raqe.agent.time_resolver import parse_time

TEMPORAL_TOKENS = {"Q1", "Q2", "Q3", "Q4", "FY", "YOY", "MOM", "QOQ"}
STOP_TOKENS = {"WHY", "WHAT", "HOW", "LAST", "LATEST", "RECENT", "REVENUE", "MARGIN", "TABLE", "SECTION"}
FY_TOKEN_PATTERN = re.compile(r"^FY\d{2,4}$")


def _parse_collection_aliases() -> dict[str, str]:
    raw = get_settings().collection_aliases
    aliases: dict[str, str] = {}
    for part in raw.split(","):
        token = part.strip()
        if not token or ":" not in token:
            continue
        alias, canonical = token.split(":", 1)
        alias = alias.strip().lower()
        canonical = canonical.strip().upper()
        if alias and canonical:
            aliases[alias] = canonical
    return aliases


def _is_valid_collection_token(token: str) -> bool:
    upper = token.upper()
    if upper in TEMPORAL_TOKENS or upper in STOP_TOKENS:
        return False
    if FY_TOKEN_PATTERN.match(upper):
        return False
    if re.fullmatch(r"Q[1-4]", upper):
        return False
    return True


def _extract_collection(question: str) -> str | None:
    aliases = _parse_collection_aliases()

    match = re.search(r"\b(?:for|in|of)\s+([A-Za-z][A-Za-z0-9_-]*)\b", question, re.IGNORECASE)
    if match:
        token = match.group(1).strip()
        alias_hit = aliases.get(token.lower())
        if alias_hit:
            return alias_hit
        if _is_valid_collection_token(token):
            return token.upper()

    lowered_question = question.lower()
    for alias, canonical in aliases.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered_question):
            return canonical

    tokens = re.findall(r"\b[A-Z]{2,}\b", question)
    if tokens:
        for token in tokens:
            alias_hit = aliases.get(token.lower())
            if alias_hit:
                return alias_hit
            if _is_valid_collection_token(token):
                return token.upper()
    return None


def parse_query(
    question: str,
    collection_override: str | None = None,
    section_hint: str | None = None,
) -> dict:
    time_context = parse_time(question)
    collection = (collection_override.strip().upper() if collection_override else _extract_collection(question))
    if not collection:
        raise ValueError("collection is required")
    collection = to_internal(collection)
    return {
        "intent": "WHY",
        "collection": collection,
        "time_context": time_context.model_dump(),
        "target": question,
        "section_hint": section_hint,
    }
