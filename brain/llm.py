"""Minimal Qwen3-8B loader + chat loop via llama.cpp (GGUF, Q4).

Run manually: python brain/llm.py
"""

import sys
from pathlib import Path

from llama_cpp import Llama

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
        n_ctx=8192,
        n_gpu_layers=-1,  # offload all layers to GPU
        verbose=False,
    )


def stream_reply(llm: Llama, messages: list[dict]):
    """Yield reply text chunks for the given chat history."""
    for chunk in llm.create_chat_completion(messages=messages, stream=True):
        delta = chunk["choices"][0]["delta"]
        if "content" in delta:
            yield delta["content"]


def strip_think(chunks):
    """Drop <think>...</think> reasoning blocks from a token stream.

    Qwen3 emits its chain-of-thought inline before the actual answer.
    Downstream consumers (API clients, title generation, the CLI by
    default) don't want it mixed into the visible reply.
    """
    buffer = ""
    in_think = False
    skip_leading_ws = True  # trim whitespace left behind right after a think block
    open_tag, close_tag = "<think>", "</think>"

    def emit(text: str):
        nonlocal skip_leading_ws
        if skip_leading_ws:
            text = text.lstrip()
            if not text:
                return
            skip_leading_ws = False
        yield text

    for piece in chunks:
        buffer += piece
        while True:
            if not in_think:
                idx = buffer.find(open_tag)
                if idx == -1:
                    hold = max(0, len(buffer) - (len(open_tag) - 1))
                    if hold:
                        yield from emit(buffer[:hold])
                        buffer = buffer[hold:]
                    break
                if idx:
                    yield from emit(buffer[:idx])
                buffer = buffer[idx + len(open_tag):]
                in_think = True
            else:
                idx = buffer.find(close_tag)
                if idx == -1:
                    buffer = buffer[-(len(close_tag) - 1):] if len(buffer) > len(close_tag) - 1 else buffer
                    break
                buffer = buffer[idx + len(close_tag):]
                in_think = False
                skip_leading_ws = True

    if not in_think and buffer:
        yield from emit(buffer)


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
