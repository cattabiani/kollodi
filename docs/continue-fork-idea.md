# Fork Continue to add selection auto-attach

**Closed 2026-10-02: Continue is dead.** Its README now says the repo is
"no longer actively maintained and is read-only for all users" (final
2.0.0 release), so the upstream PR can never land. Replaced by Cline, then Twinny —
see [vscode-frontend.md](vscode-frontend.md). The implementation stays on the fork
(cattabiani/continue, branch `feat/auto-attach-selection`) as a
reference. Everything below
is the historical record.

Implementation done 2026-09-27; waiting on final manual test + PR. RAG for Kollodi itself is a separate,
unrelated track — doesn't block or get blocked by this.

## Final scope (superseded an earlier, abandoned design — see below)

Auto-attach the current text selection to **every outgoing message**,
not just when starting a new chat. Toggle, default off. No dedup: the
current selection is attached on every send (dedup was built, then
dropped as not worth the complexity, 2026-09-23). Selections over 500
lines are skipped (likely an accidental "select all"). VS Code only —
the toggle is hidden in JetBrains. No cursor-position tracking (dropped;
selection content only, for now). The attached snippet is shown
explicitly in the chat input as a removable code block (reusing the
same visible mechanism Ctrl+L/Ctrl+Shift+L already use) rather than
being silently invisible in the composer — simplest option, matches
existing UI patterns, revisit only if it turns out to be noisy in
practice.

### Abandoned earlier design (do not resurrect without rereading this)

First attempt: auto-attach only when a *new session* starts (mirroring
`useCurrentFileAsContext`/#5670's exact trigger — hooking
`continue.newSession`). Built, tested, worked — then discarded as
"almost useless" once actually tried: it still required Ctrl+L for
every message within an ongoing chat, which was the actual friction to
remove. `git log` in the `continue` fork will show this was reverted;
don't re-add a `continue.newSession` hook for this feature.

Also discovered along the way: Ctrl+Shift+L (`continue.focusContinueInputWithoutClear`)
already attaches a selection *without* starting a new chat — so
"mid-conversation attach" already existed, manually. The real ask was
never "make mid-conversation attach possible" but "make it automatic,
no keypress."

## Background / precedent research

Continue auto-attaches the *current file* as a removable mention when a
new chat starts (setting `useCurrentFileAsContext`, from PR
continuedev/continue#5670, itself only partially solving
continuedev/continue#5457's original three-part ask: file + selection +
codebase). Selection auto-attach was never built by Continue.
Maintainer (sestinj) was receptive to a togglable setting for this
class of feature in #5457, having previously declined default-on due
to cost/prompt-cleanliness feedback on the file version.

## Public comment

Commented on the closed issue #5457 (couldn't open a new issue or
discussion from outside the repo — `blank_issues_enabled: false` and
`has_discussions: false` on the actual repo, despite CONTRIBUTING.md
and the issue template's contact_links claiming Discussions works).
Tagged @sestinj and @s-h-a-d-o-w. Posted 2026-09-23, then **edited**
once the scope changed (new-session idea dropped, replaced with the
per-message + dedup design above) — the edit explains the pivot and
why (ctrl-L only fires for new chats; ctrl-shift-L already does manual
mid-chat attach; wanted it automatic instead).

## Task checklist

- [x] Fork `continuedev/continue`, clone to `/home/katta/projects/continue`
      (fork: github.com/cattabiani/continue, origin+upstream remotes set)
- [x] Dev environment: Node v20.20.1 via nvm (`.nvmrc`-pinned), global
      vite, `scripts/install-dependencies.sh` — clean, no errors.
      `.envrc` (nvm use) added to `continue/` + `.git/info/exclude`
      (local-only, never part of a PR diff).
- [x] Commented on #5457 per CONTRIBUTING.md, then edited it once scope
      changed (see "Public comment" above).
- [x] Verified Extension Development Host test loop: Run and Debug ->
      "Launch extension" opens a second VS Code window running the
      fork's source live. Verify via "Developer: Show Running
      Extensions", **not** the Extensions panel (that panel can show
      stale/marketplace metadata even when the dev version is genuinely
      running — same extension ID as the Marketplace one). Full
      stop+restart of the debug session (not just window reload) is
      the reliable way to pick up changes with certainty.
      `extensions/.continue-debug/config.yaml` (gitignored) holds a
      Kollodi model entry mirroring the real `~/.continue/config.yaml`,
      so the Host window has a model to test against.
- [x] Implemented final design (see "Code map" below). `tsc --noEmit`
      clean on all 3 touched packages (core, gui, extensions/vscode).
- [x] First manual test round (user, 2026-09-23, via real Kollodi request
      log inspection): confirmed working correctly across ~14 messages
      in one growing conversation — unchanged selection not resent,
      content change (even same line) resent, location change resent,
      reverting to older-but-not-most-recent content resent (expected:
      only last hash tracked, not full history), repeated no-ops
      correctly skipped twice in a row.
- [x] Found + fixed a real bug from that testing: dedup was keyed only
      by filepath, globally across the whole extension — so (a) the
      same selection sent in chat A got incorrectly skipped in chat B,
      and (b) starting a brand-new chat's first message could get
      skipped too, if that exact content had been sent in *any* other
      chat previously. Fixed by scoping the dedup key to
      `(sessionId, filepath)` instead of `filepath` alone — passed
      through the protocol request now (`{ sessionId: string }` payload
      on `getAutoAttachSelection`). Decided (no special-casing): a new
      chat's first message SHOULD auto-attach like any other message;
      this fix makes that happen for free (fresh session = no prior
      dedup entries = never spuriously skipped).
- [x] Dropped dedup entirely (superseding the fix above) and added a
      500-line cap on auto-attached selections.
- [x] Fixed a JetBrains hang (2026-09-27): `onEnter` awaited
      `getAutoAttachSelection` on every send, but JetBrains'
      `IdeProtocolClient` never replies to unknown message types and the
      GUI's `request()` has no timeout, so Enter would have silently
      stopped sending. Now the GUI only asks when the setting is on and
      `!isJetBrains()`; the toggle is hidden in JetBrains.
- [x] Review pass (2026-09-27) fixed three more bugs: Enter on an empty
      input sent a code-only message (attach now runs after the
      empty-input check); Edit mode got the selection attached twice
      (skipped now); a second Enter while waiting for the selection sent
      the message twice (guarded in `autoAttachSelection.ts`). Host no
      longer re-reads config per send.
- [x] Tests: `autoAttachSelection.test.ts` (4) + `insertHighlightedCodeBlock.test.ts`
      (3). gui/core/vscode suites + `tsc --noEmit` clean; only failures
      are `core/llm/llm.test.ts` API-key tests (pass with
      `IGNORE_API_KEY_TESTS=true`).
- [x] Squashed to one commit, force-pushed to the fork; fork PR
      cattabiani/continue#1 holds the final description. Pre-squash
      history kept locally as `backup/auto-attach-selection-pre-squash`.
- [x] Manual test + demo clip (`~/Videos/pr-demo.mp4`), verified via
      the Kollodi request log (`kollodi serve --debug`).
- [ ] Optional: check Edit mode (Ctrl+I) doesn't attach an extra block.
- [ ] Open PR against continuedev/continue, referencing #5457; sign the
      CLA via comment when the bot asks.

## Code map (current design, implemented 2026-09-23)

**New protocol message** (webview asks host "what should I attach, if
anything" at send-time — a real request/response, not the host pushing
unprompted, unlike `newSession`/`highlightedCode`):
- `core/protocol/ideWebview.ts` — added
  `getAutoAttachSelection: [undefined, RangeInFileWithContents | null]`
  to `ToIdeFromWebviewProtocol`. Precedent for a real (non-void) webview
  -> host response: `"jetbrains/getColors"` in the same file.

**Host-side handler** (`extensions/vscode/src/extension/VsCodeMessenger.ts`,
registered via `this.onWebview("getAutoAttachSelection", ...)`, next to
the existing `"edit/addCurrentSelection"` handler):
- Reads `config.experimental.useCurrentSelectionAsContext`; `null` if off.
- Reuses `getRangeInFileWithContents(false)` from
  `extensions/vscode/src/util/addCode.ts` (the same function Ctrl+L /
  Ctrl+Shift+L already use) to get the live selection; `null` if empty.
- Returns `null` for selections over `MAX_AUTO_ATTACH_SELECTION_LINES`
  (500).

**Webview side** (`gui/src/components/mainInput/TipTapEditor/utils/editorConfig.ts`,
inside `onEnter`, gated on `props.isMainInput`, the setting being on
(read from redux), and `!isJetBrains()`): before reading
`editor.getJSON()` to build the outgoing message, `await`s
`ideMessenger.request("getAutoAttachSelection", undefined)`; if a
non-null result comes back, inserts it as a visible, removable code
block via a new shared helper,
`gui/src/components/mainInput/TipTapEditor/utils/insertHighlightedCodeBlock.ts`
(extracted from the existing `"highlightedCode"` listener in
`useMainEditorWebviewListeners.ts`, which now calls the same shared
helper instead of its own inline copy — no behavior change there,
pure dedup of the insertion logic).

**Setting** (schema/type/UI, unchanged shape from the earlier design,
only the description text updated): `useCurrentSelectionAsContext` in
`core/index.d.ts` + `core/config/sharedConfig.ts` (Zod schema + merge
logic) + `gui/src/pages/config/sections/UserSettingsSection.tsx`
("Auto-attach Current Selection", under Settings -> Experimental,
hidden in JetBrains).

**Why a live round-trip, not a cached/pushed value:** live selection
state only exists in the extension host (`vscode.window.activeTextEditor`),
unreachable from the sandboxed webview. Since the selection can change
freely between keystrokes, asking fresh at the exact moment of send
(rather than a host push cached in Redux) avoids staleness with no
extra plumbing (no continuous `onDidChangeTextEditorSelection` push
channel needed).
