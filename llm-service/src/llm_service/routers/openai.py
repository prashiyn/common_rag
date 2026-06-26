from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Literal

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from llm_service.llms.gateway import get_models, run_completion, run_embeddings
from llm_service.llms.models import (
    CompletionRequest,
    EmbeddingRequest,
    JsonSchemaPayload,
    ResponseFormatJsonObject,
    ResponseFormatJsonSchema,
)
from llm_service.llms.provider import infer_provider, normalize_litellm_model

router = APIRouter()


class OpenAIChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool", "developer"]
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class OpenAIResponseFormatJsonSchema(BaseModel):
    name: str
    schema_: dict[str, Any] = Field(..., alias="schema")
    strict: bool | None = None


class OpenAIResponseFormat(BaseModel):
    type: Literal["text", "json_object", "json_schema"]
    json_schema: OpenAIResponseFormatJsonSchema | None = None


class OpenAIChatCompletionRequest(BaseModel):
    model: str
    messages: list[OpenAIChatMessage] = Field(..., min_length=1)
    temperature: float | None = Field(None, ge=0, le=2)
    top_p: float | None = Field(None, ge=0, le=1)
    max_tokens: int | None = Field(None, ge=1)
    max_completion_tokens: int | None = Field(None, ge=1)
    n: int | None = Field(None, ge=1, le=128)
    stream: bool | None = False
    stop: str | list[str] | None = None
    presence_penalty: float | None = Field(None, ge=-2, le=2)
    frequency_penalty: float | None = Field(None, ge=-2, le=2)
    user: str | None = None
    response_format: OpenAIResponseFormat | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = None


class OpenAIChatCompletionMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str | None = None


class OpenAIChatCompletionChoice(BaseModel):
    index: int
    message: OpenAIChatCompletionMessage
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter", "function_call"] | None = "stop"


class OpenAICompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenAIChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[OpenAIChatCompletionChoice]
    usage: OpenAICompletionUsage


class OpenAIModelCard(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str


class OpenAIModelListResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[OpenAIModelCard]


class OpenAIEmbeddingRequest(BaseModel):
    model: str
    input: str | list[str]
    encoding_format: Literal["float", "base64"] | None = None
    dimensions: int | None = Field(None, ge=1)
    user: str | None = None


class OpenAIEmbeddingObject(BaseModel):
    object: Literal["embedding"] = "embedding"
    index: int
    embedding: list[float] | str


class OpenAIEmbeddingListResponse(BaseModel):
    object: Literal["list"] = "list"
    model: str
    data: list[OpenAIEmbeddingObject]
    usage: dict[str, int]


def _normalize_messages(messages: list[OpenAIChatMessage]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for msg in messages:
        role = msg.role
        if role in ("tool", "developer"):
            role = "user"
        content = msg.content
        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text" and part.get("text"):
                        text_parts.append(str(part["text"]))
                    elif part.get("text"):
                        text_parts.append(str(part["text"]))
            content = "\n".join(text_parts)
        elif content is None:
            content = ""
        else:
            content = str(content)
        out.append({"role": role, "content": content})
    return out


def _map_response_format(
    rf: OpenAIResponseFormat | None,
) -> ResponseFormatJsonObject | ResponseFormatJsonSchema | None:
    if rf is None or rf.type == "text":
        return None
    if rf.type == "json_object":
        return ResponseFormatJsonObject(type="json_object")
    if rf.type == "json_schema":
        if rf.json_schema is None:
            raise HTTPException(status_code=400, detail="response_format.json_schema is required for type=json_schema")
        return ResponseFormatJsonSchema(
            type="json_schema",
            json_schema=JsonSchemaPayload(
                name=rf.json_schema.name,
                schema=rf.json_schema.schema_,
                strict=rf.json_schema.strict,
            ),
        )
    return None


def _owned_by(model_id: str) -> str:
    if "/" in model_id:
        return model_id.split("/", 1)[0]
    return infer_provider(model_id)


@router.post("/chat/completions", response_model=OpenAIChatCompletionResponse)
async def chat_completions(req: OpenAIChatCompletionRequest) -> OpenAIChatCompletionResponse:
    if req.stream:
        raise HTTPException(
            status_code=400,
            detail="Streaming is not supported. Set stream=false or omit stream.",
        )
    if req.n is not None and req.n > 1:
        raise HTTPException(status_code=400, detail="Only n=1 is supported.")

    provider = infer_provider(req.model)
    litellm_model = normalize_litellm_model(req.model, provider)
    logger.debug(
        "POST /v1/chat/completions request_model=%s provider=%s litellm_model=%s messages=%d",
        req.model,
        provider,
        litellm_model,
        len(req.messages),
    )
    internal = CompletionRequest(
        provider=provider,
        model=litellm_model,
        messages=_normalize_messages(req.messages),
        reasoning_effort=req.reasoning_effort,
        response_format=_map_response_format(req.response_format),
    )
    result = await run_completion(internal, route="POST /v1/chat/completions")
    usage = OpenAICompletionUsage()
    return OpenAIChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        created=int(time.time()),
        model=req.model,
        choices=[
            OpenAIChatCompletionChoice(
                index=0,
                message=OpenAIChatCompletionMessage(role="assistant", content=result.content),
                finish_reason="stop",
            )
        ],
        usage=usage,
    )


@router.get("/models", response_model=OpenAIModelListResponse)
async def list_models() -> OpenAIModelListResponse:
    cfg = get_models()
    created = int(time.time())
    data = [
        OpenAIModelCard(id=model_id, created=created, owned_by=_owned_by(model_id))
        for model_id in cfg.models
    ]
    return OpenAIModelListResponse(data=data)


@router.post("/embeddings", response_model=OpenAIEmbeddingListResponse)
async def create_embeddings(req: OpenAIEmbeddingRequest) -> OpenAIEmbeddingListResponse:
    provider = infer_provider(req.model)
    litellm_model = normalize_litellm_model(req.model, provider)
    internal = EmbeddingRequest(
        provider=provider,
        model=litellm_model,
        input=req.input,
        encoding_format=req.encoding_format,
        dimensions=req.dimensions,
        user=req.user,
    )
    result = await run_embeddings(internal)
    usage = result.usage or {}
    openai_usage = {
        "prompt_tokens": int(usage.get("prompt_tokens", usage.get("total_tokens", 0)) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
    }
    return OpenAIEmbeddingListResponse(
        model=result.model or req.model,
        data=[
            OpenAIEmbeddingObject(index=item.index, embedding=item.embedding)
            for item in result.data
        ],
        usage=openai_usage,
    )
