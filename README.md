# Kollodi

A locally-run personal AI assistant. Permissive-license models only (MIT/Apache 2.0).

## Status

Prototype stage: Qwen3-8B (Apache 2.0) running locally via llama.cpp, manual terminal chat only.

## Layout

- `core/` — orchestrator + model manager (future)
- `brain/` — LLM wrapper (`llm.py`)
- `voice/` — STT/TTS (future)
- `vision/` — image understanding/generation (future)
- `memory/` — RAG (future)
- `api/` — FastAPI server (future)
- `tests/`
- `docker/`
- `docs/`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124
pip install -r requirements.txt
```

No system CUDA toolkit is required — CUDA runtime libs come from the
`nvidia-cuda-runtime-cu12` / `nvidia-cublas-cu12` pip packages. Before running,
source the generated env helper so llama.cpp can find them:

```bash
source .venv/kollodi_env.sh
```

Download a Qwen3-8B GGUF (Q4_K_M quant) into `brain/models/qwen3-8b-q4_k_m.gguf`
(e.g. from `Qwen/Qwen3-8B-GGUF` on Hugging Face).

## Run

```bash
source .venv/bin/activate
source .venv/kollodi_env.sh
python brain/llm.py
```
