# Cline as Kollodi's VS Code front end

Replaces Continue (dead as of 2026-10-02, see
[continue-fork-idea.md](continue-fork-idea.md)).

## Why Cline

Picked as the industry standard, not for any specific feature: the most
widely used open-source VS Code coding agent (Apache-2.0, ~70k stars,
330+ contributors, releases several times a week). Alternatives checked
2026-10-02:

- Kilo Code (MIT) — alive, but a company product built around its own
  model gateway; now rebuilt on OpenCode.
- OpenCode (MIT) — the terminal standard, not a VS Code sidebar.
- Roo Code, Void — archived.
- Twinny (MIT) — alive but effectively a one-person project.
- Tabby, Zed — not MIT/Apache.

## Setup

1. `kollodi serve` (add `--debug` to log requests to
   `/tmp/kollodi_requests.jsonl`).
2. Cline settings → API Provider: **OpenAI Compatible**
   - Base URL: `http://localhost:8000/v1`
   - API key: anything (Kollodi ignores it)
   - Model ID: `kollodi`
   - Context window: `32768`

Cline stores this in `~/.cline/data/settings/providers.json`, shared by
its VS Code extension, CLI and desktop app.

## What Kollodi needed for it

Cline is an agent: it talks to OpenAI-compatible providers with native
tool calling and a large system prompt. The server previously handled
plain text chat only. Changes (2026-10-02):

- `n_ctx` 8192 → 32768, with `flash_attn=True`. Without flash attention
  32k fails to allocate; with it, ~10.8GB VRAM in use (desktop
  included) after a ~20k-token prompt.
- Request schema accepts `tools`, content-part arrays, `null` content,
  and `tool` role messages.
- `tools` are rendered by Qwen3's own chat template (via
  llama-cpp-python); the `<tool_call>` blocks it emits are parsed into
  OpenAI `tool_calls` (`split_tool_calls` in `brain/llm.py`). Each call
  is streamed as one whole delta, since it only parses once complete.

## Thinking, controlled from Cline

Cline's **Reasoning Effort** selector (OpenAI Compatible provider
settings, set separately for Plan and Act mode) turns Qwen3's thinking
on and off:

- `none` (Cline's default) sends no `reasoning_effort` → thinking off,
  via the chat template's `enable_thinking=false` switch.
- Any level (`low`/`medium`/`high`…) → thinking on. Qwen3 has no budget
  control, so the levels all behave the same.

The thinking is streamed as `reasoning_content` (the DeepSeek/vLLM field
Cline's AI SDK reads), so Cline shows it as reasoning, separate from the
answer.

## Open questions

- Whether Qwen3-8B is capable enough to drive Cline's agent loop on real
  tasks — to be found out by using it.
- Selection auto-attach (the Continue feature): missed right away. Cline's
  "Add to Cline" (Ctrl+L, rebound in `~/.config/Code/User/keybindings.json`
  since Cline's `cmd+'` never fires on Linux) is manual, and it inserts a
  file mention next to the snippet, so the whole file is sent too.
  Asked to implement it on cline/cline#12463 (existing feature request),
  tagging @saoudrizwan, 2026-10-02:
  https://github.com/cline/cline/discussions/12463#discussioncomment-18716733
  CONTRIBUTING requires maintainer approval before feature PRs, so no
  development until a reply. Odds are low: no maintainer replies on the
  ~56 latest feature requests sampled. Fallback if the terminal is
  acceptable: OpenCode already does this (auto-attaches the selection,
  snippet only).
  Fork/clone not done yet; cloning Cline needs `git-lfs` installed.
