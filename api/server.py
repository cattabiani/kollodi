"""OpenAI-compatible chat completions server for Kollodi.

Run: uvicorn api.server:app --host 0.0.0.0 --port 8000
"""

import json
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from brain.llm import STYLE_PROMPT, load_model, stream_reply, strip_think
from api.schemas import ChatCompletionRequest, ChatCompletionResponse

llm = None

# Temporary: log raw incoming requests verbatim, to see exactly what a
# client (e.g. Continue) sends, regardless of what its docs/settings claim.
REQUEST_LOG = Path("/tmp/kollodi_requests.jsonl")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm
    llm = load_model()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest):
    with REQUEST_LOG.open("a") as f:
        f.write(request.model_dump_json() + "\n")

    messages = [{"role": "system", "content": STYLE_PROMPT}]
    messages += [m.model_dump() for m in request.messages]

    if request.stream:
        return StreamingResponse(
            _stream_chunks(request.model, messages),
            media_type="text/event-stream",
        )

    reply = "".join(strip_think(stream_reply(llm, messages)))
    return ChatCompletionResponse.from_reply(request.model, reply)


def _stream_chunks(model: str, messages: list[dict]):
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    for piece in strip_think(stream_reply(llm, messages)):
        chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(chunk)}\n\n"

    final_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"
