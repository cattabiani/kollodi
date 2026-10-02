"""Minimal Qwen3-8B loader + chat loop via llama.cpp (GGUF, Q4).

Run manually: python brain/llm.py
"""

import json
import sys
from pathlib import Path

from llama_cpp import Llama
from llama_cpp.llama_chat_format import Jinja2ChatFormatter

MODEL_PATH = Path(__file__).parent / "models" / "Qwen3-8B-Q4_K_M.gguf"
STYLE_PROMPT_PATH = Path(__file__).parent / "system_prompt.txt"

STYLE_PROMPT = STYLE_PROMPT_PATH.read_text().strip()

SYSTEM_PROMPT = STYLE_PROMPT


def load_model() -> Llama:
    if not MODEL_PATH.exists():
        sys.exit(
            f"Model not found at {MODEL_PATH}\n"
            "Download a Qwen3-8B GGUF (Q4_K_M) file there, e.g. from "
            "Qwen/Qwen3-8B-GGUF on Hugging Face."
        )
    return Llama(
        model_path=str(MODEL_PATH),
        # 32k fits in 12GB only with flash attention (~10.8GB measured with
        # a ~20k-token prompt); without it context creation fails. Agentic
        # clients like Cline need the room: their system prompt is large.
        n_ctx=32768,
        flash_attn=True,
        n_gpu_layers=-1,  # offload all layers to GPU
        verbose=False,
    )


def stream_reply(
    llm: Llama, messages: list[dict], tools: list[dict] | None = None, think: bool = True
):
    """Yield reply text chunks for the given chat history.

    `tools` (OpenAI format) are rendered into the prompt by the model's own
    chat template; Qwen3 answers with inline <tool_call> blocks, which
    split_tool_calls() pulls out of the stream.

    `think=False` uses the template's `enable_thinking` switch (pre-fills an
    empty think block). create_chat_completion() can't pass template
    variables, so the prompt is rendered here and run as a raw completion.
    """
    result = _chat_formatter(llm)(messages=messages, tools=tools, enable_thinking=think)
    prompt = llm.tokenize(result.prompt.encode("utf-8"), add_bos=False, special=True)
    for chunk in llm.create_completion(prompt=prompt, stop=result.stop, max_tokens=None, stream=True):
        yield chunk["choices"][0]["text"]


def _chat_formatter(llm: Llama) -> Jinja2ChatFormatter:
    if not hasattr(llm, "_kollodi_formatter"):
        llm._kollodi_formatter = Jinja2ChatFormatter(
            template=llm.metadata["tokenizer.chat_template"],
            eos_token=llm._model.token_get_text(llm.token_eos()),
            bos_token=llm._model.token_get_text(llm.token_bos()),
        )
    return llm._kollodi_formatter


def split_think(chunks):
    """Split a token stream into ("reasoning", str) and ("text", str) pieces.

    Qwen3 emits its chain-of-thought inline, in a <think>...</think> block
    before the actual answer. Pieces are yielded as they arrive; leading
    whitespace of each section is trimmed.
    """
    buffer = ""
    in_think = False
    skip_leading_ws = True
    open_tag, close_tag = "<think>", "</think>"

    def emit(text: str):
        nonlocal skip_leading_ws
        if skip_leading_ws:
            text = text.lstrip()
            if not text:
                return
            skip_leading_ws = False
        yield ("reasoning" if in_think else "text"), text

    for piece in chunks:
        buffer += piece
        while True:
            tag = close_tag if in_think else open_tag
            idx = buffer.find(tag)
            if idx == -1:
                # Hold back a possible partial tag at the end of the buffer.
                hold = max(0, len(buffer) - (len(tag) - 1))
                if hold:
                    yield from emit(buffer[:hold])
                    buffer = buffer[hold:]
                break
            if idx:
                yield from emit(buffer[:idx])
            buffer = buffer[idx + len(tag):]
            in_think = not in_think
            skip_leading_ws = True

    if buffer:
        yield from emit(buffer)


def strip_think(chunks):
    """Drop <think>...</think> reasoning blocks from a token stream.

    For consumers that don't want the reasoning (title generation, the CLI
    by default).
    """
    for kind, text in split_think(chunks):
        if kind == "text":
            yield text


def split_tool_calls(chunks):
    """Pull tool calls out of the ("text", str) pieces from split_think().

    Yields ("text", str) pieces as they arrive and ("tool_call", dict) for
    each complete <tool_call>{"name": ..., "arguments": {...}}</tool_call>
    block Qwen3 emits. A block that isn't valid JSON is passed on as text.
    Other pieces (reasoning) pass through unchanged.
    """
    buffer = ""
    in_call = False
    open_tag, close_tag = "<tool_call>", "</tool_call>"

    for kind, piece in chunks:
        if kind != "text":
            yield kind, piece
            continue
        buffer += piece
        while True:
            if not in_call:
                idx = buffer.find(open_tag)
                if idx == -1:
                    hold = max(0, len(buffer) - (len(open_tag) - 1))
                    if hold:
                        yield "text", buffer[:hold]
                        buffer = buffer[hold:]
                    break
                if idx:
                    yield "text", buffer[:idx]
                buffer = buffer[idx + len(open_tag):]
                in_call = True
            else:
                idx = buffer.find(close_tag)
                if idx == -1:
                    break
                raw = buffer[:idx]
                buffer = buffer[idx + len(close_tag):].lstrip()
                in_call = False
                try:
                    call = json.loads(raw)
                    if not isinstance(call, dict) or "name" not in call:
                        raise ValueError
                except ValueError:
                    yield "text", open_tag + raw + close_tag
                    continue
                yield "tool_call", call

    if buffer:
        yield "text", (open_tag + buffer) if in_call else buffer


def chat_loop(debug: bool = False) -> None:
    llm = load_model()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("Kollodi (Qwen3-8B) ready. Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        print("\nQwen: ", end="", flush=True)
        reply = ""
        pieces = stream_reply(llm, messages)
        if not debug:
            pieces = strip_think(pieces)
        for piece in pieces:
            print(piece, end="", flush=True)
            reply += piece
        print("\n")
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    chat_loop(debug="--debug" in sys.argv)
