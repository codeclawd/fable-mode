# Fable mode rework — reliable activation + Claude Code fidelity

**Date:** 2026-07-03 · **Branch:** cross-platform-install (new work should move to its own branch) · **Status:** draft, awaiting user review

## Problem

The core of fable-mode — playbook injection via `fable-trigger.py` — has **never fired once** for a real
user session. Evidence gathered on 2026-07-03:

- Zero `fable-loaded-*` session markers in `%TEMP%` before today; zero "Fable mode active" injections in
  any transcript under `~/.claude/projects/` (the only mentions are today's manual probes).
- The effort path requires `effort.level` in the hook payload or `CLAUDE_EFFORT` in the hook's
  environment. On the Claude Code versions the user actually ran (≤ 2.1.198), neither reached the hook;
  today's headless probes fired only because `CLAUDE_EFFORT=xhigh` leaked in from the investigating
  session's tool environment.
- The phrase path ("use fable" / "fable mode" / "load fable") was never typed.
- By contrast, `test-after-edit.py` (PostToolUse) works and has worked — 36 sessions with its output
  since June 29, plus a live green run during this investigation (`pytest -q`, 4.6s).

Secondary problems:

- `shell/fable.{zsh,ps1}` does not pin a model. The README promises "Opus 4.8 + Fable prompt"; with the
  user's default model now `claude-fable-5`, `fable` would launch the real Fable 5 with the leaked
  *consumer* prompt appended on top — double-prompting, not emulation.
- The appended `fable-system.md` is the claude.ai consumer prompt (~1,600 lines): artifacts/storage
  APIs, MCP app suggestions, copyright rules — dead weight and occasional contradictions in a terminal.
  The README itself admits this ("trim to the claude_behavior section").
- There is no actual *skill*: activation is a regex in a hook, undiscoverable and invisible.

## Goal

"Реально работал как fable": (1) activation that fires deterministically, on every supported Claude
Code version, visibly; (2) emulation content that matches how Fable actually behaves *in Claude Code*,
not in a chat tab.

## Design (chosen approach: hybrid activation)

### 1. Launcher pins the model and declares the mode

`shell/fable.zsh`:

```zsh
fable() {
  FABLE_MODE=1 claude --model claude-opus-4-8 \
    --append-system-prompt-file "$HOME/.claude/fable-code.md" --effort xhigh "$@"
}
```

`shell/fable.ps1`: same flags; sets `$env:FABLE_MODE = "1"` before `claude` and removes it in
`finally`. Both keep `@args`/`"$@"` passthrough. `--model claude-opus-4-8` makes the README's promise
true regardless of the user's default model. The appended file becomes the new `fable-code.md`
(see §3); the consumer `fable-system.md` stays in the repo for reference and claude.ai use.

### 2. `fable-trigger.py` becomes dual-event

Registered for **SessionStart** and **UserPromptSubmit** (settings.fragment.json + merge_settings.py);
the script branches on `hook_event_name`:

- **SessionStart** (`FABLE_MODE=1` in env): inject FABLE_PLAYBOOK.md as `additionalContext` — the same
  mechanism the superpowers plugin uses, proven to work on every version in evidence. Sources
  `startup`/`clear`/`compact` always inject and (re)write the marker — after a compaction the earlier
  injection is gone from context, so the marker must not suppress it. Source `resume` injects only when
  the marker is absent (context usually survives a resume).
- **UserPromptSubmit** (unchanged paths + one new): phrase trigger always injects; effort path
  (payload `effort.level` → `CLAUDE_EFFORT` env) injects once per session — it is now documented and
  working on ≥ 2.1.199; `FABLE_MODE=1` also injects once per session as a belt-and-suspenders for
  sessions whose settings predate the SessionStart registration.

Marker files stay in `tempfile.gettempdir()`, keyed by session_id, shared by both events.

### 3. New `fable-code.md` — the Claude Code-native behavior layer

An **original distillation** (not a verbatim prompt dump) of how Fable 5 operates inside Claude Code,
which the consumer prompt cannot express. Sections:

- **Final-message contract:** everything the user needs lives in the last message of the turn; lead
  with the outcome ("what happened / what was found" in sentence one); supporting detail after.
- **Readable over concise:** shorten by *selecting* what matters, not by compressing prose into
  fragments, arrow chains (`A → B → fails`), or invented shorthand; complete sentences; no codenames
  the reader must reverse-engineer; explain in place rather than referencing earlier labels.
- **Working rhythm:** one line on intent before the first tool call; surface load-bearing findings and
  direction changes when they happen; otherwise no step-narration between tool calls.
- **Tool discipline:** batch independent calls in one block; structured tools (Grep/Glob/Read) over
  shell pipelines; `file:line` references; read the exact region before editing it *this session*;
  your own edit invalidates your last read; absolute paths.
- **Code & comments:** match surrounding idiom; a comment states only a constraint the code can't
  show — never provenance or PR-narration.
- **Autonomy & honesty:** proceed on reversible in-scope actions; confirm before irreversible or
  outward-facing ones; inspect before overwrite/delete; report failures with output, state skips,
  say "done" only after verification. When the user is *describing* a problem, deliver the assessment
  and stop — don't auto-fix.
- **End-of-turn rule:** if the closing paragraph is a plan, promise, or question answerable by a tool,
  keep working instead of ending the turn.

Provenance labelled honestly in the file header (distilled from observed first-party Fable 5 Claude
Code behavior, 2026-07). Target ≤ 250 lines.

### 4. `skills/fable/SKILL.md` — a real skill

`/fable` (user-invocable, model-invocable on "fable mode" phrasing). Body: read
`~/.claude/FABLE_PLAYBOOK.md` and `~/.claude/fable-code.md`, adopt as standing discipline for the
session, confirm activation in one line. Installer copies to `~/.claude/skills/fable/`; uninstaller
removes it.

### 5. Playbook voice-layer amendment

`FABLE_PLAYBOOK.md` gains a short "Claude Code layer (first-party)" subsection under the voice layer:
final-message completeness, readable-over-concise (anti-fragment, anti-arrow-chain), assessment mode.
Corrects the current layer's over-weighting of silence. Existing measured sections untouched.

### 6. Install / uninstall / tests / docs

- `install.py`: copy `fable-code.md`, `skills/fable/`; merge SessionStart hook entry.
- `uninstall.py`: remove both; strip the SessionStart entry (leave foreign hooks intact, as today).
- `settings.fragment.json`: add the SessionStart registration.
- Tests (pytest, stdlib-only, cross-platform): fable-trigger SessionStart × {FABLE_MODE set/unset},
  UserPromptSubmit × {phrase, effort payload, CLAUDE_EFFORT env, FABLE_MODE, none}, marker dedupe
  across events, uninstall round-trip including the new entries.
- README: quickstart unchanged; "what's in the bundle" and honest-ceiling sections updated;
  CHANGELOG entry.

## Alternatives considered

- **Everything via `--append-system-prompt-file`** (launcher concatenates prompt+playbook): simplest,
  but plain `claude` sessions get nothing and the hook path stays broken. Rejected as sole mechanism;
  the launcher *does* carry `fable-code.md` this way.
- **Skill-only activation:** zero background cost but "always-on" discipline becomes opt-in per
  session; the measured finding (verification dies on willpower) argues against. Kept as one of three
  activation paths, not the only one.

## Out of scope

- Modifying `test-after-edit.py` (works; has its own WIP on this branch).
- Re-measuring the trace statistics in FABLE_PLAYBOOK.md.
- The repo's pending uncommitted WIP (CHANGELOG/SECURITY/test-after-edit changes) — left as-is.

## Decisions taken on the user's behalf (flag on review)

1. Hybrid activation chosen (recommended option; user was AFK at the architecture question).
2. Launcher default switches from consumer `fable-system.md` to the new `fable-code.md`; the consumer
   prompt remains bundled. Veto restores the old flag value in one line.
3. Model pinned to `claude-opus-4-8` explicitly (product premise), not `opus` alias.
