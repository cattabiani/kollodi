"""Request/response shapes for the OpenAI-compatible chat completions endpoint."""

import time
import uuid

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "kollodi"
    messages: list[ChatMessage]
    stream: bool = False


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]

    @classmethod
    def from_reply(cls, model: str, reply: str) -> "ChatCompletionResponse":
        return cls(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=model,
            choices=[
                ChatCompletionChoice(
                    message=ChatMessage(role="assistant", content=reply)
                )
            ],
        )
