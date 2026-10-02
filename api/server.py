"""OpenAI-compatible chat completions server for Kollodi.

Run: uvicorn api.server:app --host 0.0.0.0 --port 8000
Set KOLLODI_DEBUG=1 (or use `kollodi serve --debug`) to log incoming requests.
"""

import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from brain.llm import STYLE_PROMPT, load_model, split_tool_calls, stream_reply, strip_think
from api.schemas import ChatCompletionRequest, ChatCompletionResponse

llm = None

# Debug only: log raw incoming requests verbatim, to see exactly what a
# client (e.g. Continue) sends, regardless of what its docs/settings claim.
DEBUG = os.environ.get("KOLLODI_DEBUG") == "1"
REQUEST_LOG = Path("/tmp/kollodi_requests.jsonl")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm
    llm = load_model()
    if DEBUG:
        print(f"Debug: logging requests to {REQUEST_LOG}")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest):
    if DEBUG:
        entry = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "request": request.model_dump(mode="json"),
        }
        with REQUEST_LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    messages = [{"role": "system", "content": STYLE_PROMPT}]
    messages += [m.to_llm() for m in request.messages]

    if request.stream:
        return StreamingResponse(
            _stream_chunks(request.model, messages, request.tools),
            media_type="text/event-stream",
        )

    reply, tool_calls = "", []
    for kind, value in _generate(messages, request.tools):
        if kind == "text":
            reply += value
        else:
            tool_calls.append(_openai_tool_call(value))
    return ChatCompletionResponse.from_reply(request.model, reply, tool_calls or None)


def _generate(messages: list[dict], tools: list[dict] | None):
    return split_tool_calls(strip_think(stream_reply(llm, messages, tools)))


def _openai_tool_call(call: dict) -> dict:
    """Qwen's {"name", "arguments": {...}} -> OpenAI's tool_calls entry."""
    arguments = call.get("arguments", {})
    return {
        "id": f"call_{uuid.uuid4().hex[:24]}",
        "type": "function",
        "function": {
            "name": call["name"],
            "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments),
        },
    }


def _stream_chunks(model: str, messages: list[dict], tools: list[dict] | None):
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    def chunk(delta: dict, finish_reason: str | None = None) -> str:
        body = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
        }
        return f"data: {json.dumps(body)}\n\n"

    n_calls = 0
    for kind, value in _generate(messages, tools):
        if kind == "text":
            yield chunk({"content": value})
        else:
            # Sent whole, in one delta: Qwen's call only parses once complete.
            yield chunk({"tool_calls": [{"index": n_calls, **_openai_tool_call(value)}]})
            n_calls += 1

    yield chunk({}, "tool_calls" if n_calls else "stop")
    yield "data: [DONE]\n\n"
