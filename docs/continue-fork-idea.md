# Idea: fork Continue to add selection auto-attach (deferred)

Not started. Revisit after Kollodi has: VS Code chat via Continue (off the
shelf) + manual Ctrl+L selection attach + basic RAG working.

## The gap

Continue auto-attaches the *current file* as a removable mention when a new
chat starts (setting `addFileContext`, from PR continuedev/continue#5670).
It does NOT auto-attach the current *selection* — that still requires
Ctrl+L (VS Code) / Cmd+J (JetBrains) manually, every message.

Requested in continuedev/continue#5457, but the merged PR only solved the
file-context third of the original ask. Last comment on that issue (from
the original requester) notes selection + codebase auto-attach were never
built. No newer issue found for just selection auto-attach as of 2026-09-22.

## Why this could be a good contribution

- Maintainers (sestinj) are receptive: declined default-on due to past
  negative feedback on cost/prompt cleanliness, but explicitly said they'd
  welcome a togglable setting and marked the issue good-first-issue.
- Precedent PR (#5670) shows the accepted pattern: new VS Code setting,
  content added as a removable mention.

## Proposed design (better than #5670's approach)

Don't dump the whole file automatically (what #5670 does). Instead:
- Auto-attach only `{filePath, selectionText, cursorLine}` — small, cheap,
  matches the cost objection that got #5457's file-context version pushback.
- Give the model a `read_file` tool it can call if it decides it needs more
  context than the selection shows (pull-on-demand, not push-everything).
- This mirrors how Claude Code's own IDE integration behaves: selection/
  cursor/path are pushed automatically and cheaply; full file content is
  only fetched via an explicit tool call (Read) when actually needed.

## Known risk

A less capable model (e.g. local Qwen3-8B in Kollodi) might re-request the
same file repeatedly instead of using the tool result efficiently.
Mitigations to test empirically once Kollodi + tool-calling exist:
- For small files (e.g. <200 lines), just include the full file upfront
  instead of relying on pull-on-demand — the on-demand design only pays
  off for larger files anyway.
- Client-side "already sent" tracking (cheap, first line of defense):
  keep a per-session map `{filePath: sha256 of last-sent content}`. Before
  honoring a `read_file` tool call, check the map:
  - checksum matches current file on disk → refuse the read, inject a
    short marker instead ("you already have server.py, unchanged") rather
    than resending content.
  - checksum missing or mismatched (file changed since last sent) → serve
    fresh content, update the stored checksum.
  This is how Claude Code's own harness behaves in practice: after a
  write/edit, the tool result says "file state is current in your
  context — no need to Read it back" instead of a cache being queried —
  the client just tracks sync state, not file bytes.
- Considered and rejected for v1: sending deltas/diffs instead of full
  content on a checksum mismatch, to cut resend cost further. Rejected
  because a smaller model has to mentally apply each diff on top of its
  memory of prior diffs, and any slip (stale mental copy, wrong line
  offset) silently corrupts its understanding with no self-correction.
  Full-resend-on-mismatch is self-correcting — always a clean authoritative
  snapshot. Only revisit deltas if resend cost is a measured problem later,
  not a hypothetical one.

## Sequencing (decided 2026-09-22)

1. Kollodi: OpenAI-compatible API server — done (`api/server.py`).
2. Install Continue, point it at Kollodi's local endpoint, verify chat
   works end to end from VS Code.
3. Verify manual Ctrl+L selection-attach works against Kollodi.
4. Add basic RAG to Kollodi (`memory/`).
5. Only then: decide whether to actually fork Continue for this feature.
