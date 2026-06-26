from pydantic import BaseModel


class TimeContext(BaseModel):
    raw_text: str
    mode: str
    start_date: str | None = None
    end_date: str | None = None
    period: str | None = None
    fiscal_year: str | None = None
    relative_window: str | None = None
    needs_fallback: bool = False


class DocumentResolutionResult(BaseModel):
    collection_id: str
    doc_ids: list[str]
    mode_used: str
    fallback_used: bool
    reason: str
