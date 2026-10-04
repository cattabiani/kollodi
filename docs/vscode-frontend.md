# Kollodi's VS Code front end: Twinny

Current front end: **Twinny** (`rjmacarthy.twinny`, MIT), since
2026-10-04. History: Continue (dead, see
[continue-fork-idea.md](continue-fork-idea.md)) → Cline (2026-10-02,
dropped, see below) → Twinny.

## Why Twinny

The feature that mattered: the current editor selection attached to
every message automatically, snippet only (not the whole file). Twinny
does this out of the box; Cline doesn't, and getting it into Cline
needed maintainer approval that never came.

- MIT throughout. The paid team licence is only a runtime key check
  for team/gateway features; solo local use is free.
- Small team (owner rjmacarthy + main dev m1ab0t), releases several
  times a week. CONTRIBUTING: open an issue, then a PR to `development`;
  no approval gate. Outside merges are rare, though.
- Sidebar chat plus agent mode; supports any OpenAI-compatible server.

## Setup

1. `kollodi serve` (add `--debug` to log requests to
   `/tmp/kollodi_requests.jsonl`).
2. Twinny → Providers → **OpenAI Compatible** as the **chat** provider:
   hostname `localhost`, port **`8000`** (preset defaults to 8080; if it
   snaps back, pick the type first and set the port last), path `/v1`,
   model `kollodi`.
3. Turn inline completion off, or don't give it a provider: Kollodi has
   no `/v1/completions` endpoint.

## Selection context: how Twinny sends it

- Plain chat: `Selected Code:\n<text>` appended to the latest message
  (`additionalContext` in `src/extension/chat/context.ts`). No file or
  line range. Nothing when nothing is selected.
- Agent mode additionally prepends one line (`editorHint` in
  `src/extension/chat/tool-sinks.ts`): `The user's active editor is
  LICENSE, with lines 18-18 selected.`, or `… cursor on line 19.` when
  nothing is selected.
- Old `Selected Code:` blocks are stripped from the history.

Known quirk (tested 2026-10-04): after deselecting, Qwen3-8B keeps
answering with the previous selection, in both modes. Its own earlier
"You have selected …" answers stay in the history, and neither silence
nor "cursor on line N" overrides them. Replaying the logged requests
with an explicit `No code is selected.` added fixed it 4/4 in both
modes. Judged too small to be worth a Twinny PR; only matters for
"what did I select?"-style questions.

## Dropped: Cline

Tried first as the industry standard (Apache-2.0, ~70k stars). Worked
with Kollodi, but its "Add to Cline" is manual (and `cmd+'` never fires
on Linux), and it inserts a file mention next to the snippet, so the
whole file is sent too. Proposed the auto-attach feature on
cline/cline#12463 (2026-10-02,
https://github.com/cline/cline/discussions/12463#discussioncomment-18716733);
no reply after two days, and CONTRIBUTING requires maintainer approval
before feature PRs (no maintainer replies on the ~56 latest feature
requests sampled). Uninstalled 2026-10-04; `~/.cline/` (settings) left
in place.

## What Kollodi's server needed for agent front ends

Done for Cline (2026-10-02), used by Twinny's agent mode too. Agent
clients use native OpenAI tool calling and a large system prompt; the
server previously handled plain text chat only.

- `n_ctx` 8192 → 32768, with `flash_attn=True`. Without flash attention
  32k fails to allocate; with it, ~10.8GB VRAM in use (desktop
  included) after a ~20k-token prompt.
- Request schema accepts `tools`, content-part arrays, `null` content,
  and `tool` role messages; unknown fields are kept so the debug log
  shows everything a client sends.
- `tools` are rendered by Qwen3's own chat template; the `<tool_call>`
  blocks it emits are parsed into OpenAI `tool_calls`
  (`split_tool_calls` in `brain/llm.py`). Each call is streamed as one
  whole delta, since it only parses once complete.

### Thinking via `reasoning_effort`

- Any `reasoning_effort` level → Qwen3 thinking on; none sent (or
  `none`/`minimal`) → off, via the chat template's
  `enable_thinking=false` switch. Qwen3 has no budget control, so the
  levels all behave the same. Built for Cline's Reasoning Effort
  selector; Twinny sends no effort, so thinking is off there.
- The thinking is streamed as `reasoning_content` (the DeepSeek/vLLM
  field), so clients that read it show it as reasoning.

## Open questions

- Whether Qwen3-8B is capable enough for agent mode on real tasks — to
  be found out by using it.
