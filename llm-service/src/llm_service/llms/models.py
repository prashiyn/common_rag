from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class JsonSchemaPayload(BaseModel):
    name: str
    schema_: dict[str, Any] = Field(..., alias="schema")
    strict: bool | None = None


class ResponseFormatJsonObject(BaseModel):
    type: Literal["json_object"]


class ResponseFormatJsonSchema(BaseModel):
    type: Literal["json_schema"]
    json_schema: JsonSchemaPayload


class CompletionRequest(BaseModel):
    provider: str = Field(..., description="Provider alias: groq, ollama, openai, anthropic")
    messages: list[dict[str, str]] = Field(..., min_length=1)
    model: str | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = None
    response_format: ResponseFormatJsonObject | ResponseFormatJsonSchema | None = None


class CompletionResponse(BaseModel):
    content: str
    parsed: Any | None = None


class ModelsResponse(BaseModel):
    default_model: str
    fallback_model: str
    models: list[str]


class EmbeddingRequest(BaseModel):
    provider: str
    input: str | list[str]
    model: str | None = None
    encoding_format: Literal["float", "base64"] | None = None
    dimensions: int | None = Field(None, ge=1)
    input_type: str | None = None
    user: str | None = None


class EmbeddingDataItem(BaseModel):
    object: str
    index: int
    embedding: list[float] | str


class EmbeddingResponse(BaseModel):
    object: str
    model: str
    data: list[EmbeddingDataItem]
    usage: dict[str, Any] | None = None
