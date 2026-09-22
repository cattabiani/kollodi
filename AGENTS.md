# Agent rules for Kollodi

## Project constraints

- **License**: only MIT/Apache 2.0 models and dependencies. No exceptions —
  needs unrestricted commercial-use credibility. Verify license before
  adding any model or ML dependency.
- **Local-first**: everything must run on a single RTX 4070Ti (12GB VRAM).
  Don't assume cloud APIs or multi-GPU setups.
- **No premature abstraction**: build only the module being worked on. Stub
  folders (`core/`, `voice/`, `vision/`, `memory/`, `api/`) exist to show
  where future code goes — don't fill them out ahead of need.

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

## Environment

- Python venv at `.venv/`, activated automatically via direnv (`.envrc`).
- CUDA runtime for llama-cpp-python comes from pip packages
  (`nvidia-cuda-runtime-cu12`, `nvidia-cublas-cu12`), not a system CUDA
  toolkit. `.venv/kollodi_env.sh` sets `LD_LIBRARY_PATH` accordingly and is
  sourced automatically by direnv.
- Model weights (`brain/models/*.gguf`) are gitignored — never commit them.

## Conventions

- Keep scripts runnable standalone from the terminal (`python brain/llm.py`)
  for manual testing — no test framework or CI wired up yet.
