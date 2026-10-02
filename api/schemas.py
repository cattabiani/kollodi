"""Request/response shapes for the OpenAI-compatible chat completions endpoint."""

import time
import uuid

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    # Clients may send a list of content parts ({"type": "text", ...});
    # assistant messages that only call tools may have no content.
    content: str | list[dict] | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None

    def to_llm(self) -> dict:
        """Flatten into the plain-dict shape the chat template expects."""
        content = self.content
        if isinstance(content, list):
            # Text only: the model can't see images, so other parts are dropped.
            content = "".join(p.get("text", "") for p in content if p.get("type") == "text")
        message = {"role": self.role, "content": content or ""}
        if self.tool_calls:
            message["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            message["tool_call_id"] = self.tool_call_id
        return message


class ChatCompletionRequest(BaseModel):
    model: str = "kollodi"
    messages: list[ChatMessage]
    stream: bool = False
    tools: list[dict] | None = None


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
    def from_reply(
        cls, model: str, reply: str, tool_calls: list[dict] | None = None
    ) -> "ChatCompletionResponse":
        return cls(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=model,
            choices=[
                ChatCompletionChoice(
                    message=ChatMessage(
                        role="assistant", content=reply, tool_calls=tool_calls
                    ),
                    finish_reason="tool_calls" if tool_calls else "stop",
                )
            ],
        )
