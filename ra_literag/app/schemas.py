"""Request/response models for RAG-Anything API."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import WORKSPACE_DEFAULT


class QueryRequest(BaseModel):
    workspace: str = Field(default=WORKSPACE_DEFAULT, description="Tenant/workspace id for data isolation")
    query: str = Field(..., description="Natural language question")
    mode: str = Field("hybrid", description="Query mode: local, global, hybrid, naive, mix, bypass")
    vlm_enhanced: bool | None = Field(None, description="Use VLM for images in context")
    system_prompt: str | None = None


class QueryResponse(BaseModel):
    answer: str


class MultimodalItem(BaseModel):
    type: str = Field(..., description="One of: table, equation, image")
    table_data: str | None = None
    table_body: str | None = None
    table_caption: str | list[str] | None = None
    table_footnote: str | list[str] | None = None
    latex: str | None = None
    equation_caption: str | None = None
    img_path: str | None = None
    image_caption: str | list[str] | None = None
    image_footnote: str | list[str] | None = None


class QueryMultimodalRequest(BaseModel):
    workspace: str = Field(default=WORKSPACE_DEFAULT, description="Tenant/workspace id")
    query: str = Field(..., description="Question in context of the given multimodal content")
    multimodal_content: list[MultimodalItem] = Field(..., description="Tables, equations, or image refs")
    mode: str = Field("hybrid", description="Query mode")


class ContentListItem(BaseModel):
    type: str = Field(..., description="text, image, table, equation, or custom")
    text: str | None = None
    img_path: str | None = None
    image_caption: list[str] | None = None
    image_footnote: list[str] | None = None
    table_body: str | None = None
    table_caption: list[str] | None = None
    table_footnote: list[str] | None = None
    latex: str | None = None
    content: str | None = None
    page_idx: int = 0


class InsertContentRequest(BaseModel):
    workspace: str = Field(default=WORKSPACE_DEFAULT, description="Tenant/workspace id")
    content_list: list[ContentListItem] = Field(..., description="Pre-parsed content items")
    file_path: str = Field("unknown_document", description="Reference name for citations")
    doc_id: str | None = None
    split_by_character: str | None = None
    split_by_character_only: bool = False


