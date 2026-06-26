"""Pure ASGI middleware: BaseHTTPMiddleware does not propagate ``scope['path']`` changes to routing."""

from __future__ import annotations

import json
from typing import Any

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from raqe.collection_namespace import (
    rewrite_collections_path,
    transform_inbound_payload,
    transform_outbound_payload,
)


async def _read_request_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            break
        if message["type"] != "http.request":
            continue
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


def _replay_receive(body: bytes) -> Receive:
    state = 0

    async def receive() -> Message:
        nonlocal state
        if state == 0:
            state = 1
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    return receive


def _method_str(scope: Scope) -> str:
    raw = scope.get("method", b"GET")
    if isinstance(raw, bytes):
        return raw.decode("ascii").upper()
    return str(raw).upper()


def _header_value(headers: Any, key: bytes) -> bytes | None:
    if not headers:
        return None
    lk = key.lower()
    for k, v in headers:
        if k.lower() == lk:
            return v
    return None


def _strip_content_length_from_start(start_msg: Message) -> Message:
    hdrs = [(k, v) for k, v in start_msg["headers"] if k.lower() != b"content-length"]
    return {"type": "http.response.start", "status": start_msg["status"], "headers": hdrs}


class CollectionNamespaceMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        scope = dict(scope)
        path = scope.get("path", "") or ""
        new_path = rewrite_collections_path(path)
        if new_path is not None:
            scope["path"] = new_path
            if "raw_path" in scope:
                scope["raw_path"] = new_path.encode("utf-8")

        inner_receive = receive
        if _method_str(scope) in ("POST", "PUT", "PATCH"):
            headers = Headers(scope=scope)
            if "application/json" in headers.get("content-type", "").lower():
                body = await _read_request_body(receive)
                if body:
                    try:
                        parsed: Any = json.loads(body.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        inner_receive = _replay_receive(body)
                    else:
                        inner_receive = _replay_receive(
                            json.dumps(transform_inbound_payload(parsed)).encode("utf-8")
                        )
                else:
                    inner_receive = _replay_receive(b"")

        messages: list[Message] = []

        async def capture_send(message: Message) -> None:
            messages.append(message)

        await self.app(scope, inner_receive, capture_send)

        i = 0
        while i < len(messages):
            msg = messages[i]
            if msg["type"] != "http.response.start":
                await send(msg)
                i += 1
                continue

            start_msg = msg
            i += 1
            body_parts: list[bytes] = []
            more = True
            while i < len(messages) and messages[i]["type"] == "http.response.body":
                body_parts.append(messages[i].get("body", b""))
                more = bool(messages[i].get("more_body", False))
                i += 1
                if not more:
                    break

            full_body = b"".join(body_parts)
            ct = _header_value(start_msg.get("headers"), b"content-type")
            if ct and b"application/json" in ct.lower() and full_body.strip():
                try:
                    data = json.loads(full_body.decode("utf-8"))
                    full_body = json.dumps(transform_outbound_payload(data), ensure_ascii=False).encode("utf-8")
                    start_msg = _strip_content_length_from_start(start_msg)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

            await send(start_msg)
            await send({"type": "http.response.body", "body": full_body, "more_body": False})
