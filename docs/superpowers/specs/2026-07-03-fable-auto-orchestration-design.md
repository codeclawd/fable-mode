# Fable mode: auto-activation, orchestration, doctor

**Date:** 2026-07-03 · **Follows:** `2026-07-03-fable-mode-rework-design.md` (implemented earlier today) · **Status:** draft, awaiting user review

## Problem

After the activation rework, Fable mode fires reliably — but only when the user launches via
`fable`, types a trigger phrase, or runs at xhigh effort. A plain `claude` session given a complex
task gets no discipline. Orchestration (ultracode) is documented only as a comment. And the class
of silent failure found this morning (installed but never firing) had no self-diagnosis tool.

## Goals

1. **Auto-activation:** a complex task activates Fable mode by itself, in any session.
2. **Orchestration:** one-flag access to ultracode plus playbook guidance on when/how to fan out.
3. **`fable doctor`:** one command that verifies the whole install/activation chain mechanically.

## Design

### 1. Complexity auto-trigger (hybrid: deterministic + model-side)

**Deterministic half — `hooks/fable-trigger.py`.** New pure function `looks_complex(prompt)`,
score-based (complex when score ≥ 2):

| Signal | Points |
|---|---|
| length ≥ 400 chars | 2 |
| fenced code block (```) or traceback marker | 2 |
| task verb, ru+en stems (сдела/добав/почин/исправ/реализу/перепиш/настро/созда/собер/интегрир/оптимизир/мигрир/разработ; implement/refactor/migrate/build/create/add/fix/debug/integrate/optimize/rewrite/design/install) | 1 |
| file path or extension (`\w+\.(py|js|ts|…)`, `/` or `\` path shapes) | 1 |
| multi-step marker (затем/потом/после этого/then/steps/numbered list) | 1 |
| ≥ 3 non-empty lines | 1 |

Wired into the UserPromptSubmit branch as a third "heavy" source (alongside effort and
FABLE_MODE): injects the playbook once per session (same marker), reason `auto`. Opt-out:
`FABLE_AUTO=0` disables the heuristic entirely; phrase/effort/FABLE_MODE paths are unaffected.
The heuristic never *blocks* anything — worst case is one 12 KB injection in a session that
didn't need it.

**Model-side half — `skills/fable/SKILL.md`.** Description gains a proactive clause: use at the
start of any non-trivial engineering task (multi-step implementation, refactor, migration, long
debugging) when the playbook is not already in context. Body gains: if the playbook content is
already present in context (hook injected it), skip the file reads and just confirm activation.

### 2. Orchestration

**Launcher flag.** `fable --ultra` (alias `-u`) inserts `--settings '{"ultracode": true}'` before
the passthrough args in both `fable.zsh` and `fable.ps1` (parsed only as the first argument).
Everything else about the launch (model pin, `fable-code.md`, xhigh, `FABLE_MODE=1`) is unchanged.

**Playbook section.** New short section "Orchestration — scale the harness to the task" appended
after Enforcement: when a task decomposes into independent units, fan out subagents in parallel
and verify adversarially (the cold `grounding-verifier` is the built-in verifier); plan-gate
before long autonomous runs; never bring multi-agent machinery to a task one context handles —
the calibration rule already in "Carried over" applies with force. Mentions `fable --ultra` as
the mechanical lever for auto-workflows.

### 3. `fable doctor`

New `hooks/fable-doctor.py` (stdlib-only, Python ≥ 3.9), installed next to the hooks it
diagnoses; invoked via the `fable doctor` launcher subcommand (first-argument dispatch, both
shells) or directly. Checks, each printed as `[ok]` / `[!!]` (failure) / `[--]` (warning/info):

1. Python version ≥ 3.9.
2. Presence of `~/.claude/`: FABLE_PLAYBOOK.md, fable-code.md, fable-system.md,
   hooks/fable-trigger.py, hooks/test-after-edit.py, skills/fable/SKILL.md,
   agents/grounding-verifier.md.
3. `settings.json` parses; SessionStart + UserPromptSubmit reference fable-trigger.py, PostToolUse
   references test-after-edit.py; the interpreter path inside each hook command exists.
4. `claude` CLI on PATH; version parsed from `claude --version` — warn (not fail) below 2.1.199
   ("effort not exposed to hooks; SessionStart path unaffected").
5. **Live fire:** runs the *installed* fable-trigger.py twice — SessionStart payload with
   FABLE_MODE=1, and UserPromptSubmit with a trigger phrase — asserting JSON output with the
   right hookEventName; cleans up its markers.
6. Injection evidence: scans the ~10 most recent transcripts under `~/.claude/projects/` for
   "Fable mode active" (info only: last-seen timestamp or "never seen").
7. `alwaysThinkingEnabled` true (warning if not).

Exit code 1 only on hard failures (missing core files, unparseable/unregistered settings, live-fire
failure); warnings and info don't fail the run. `FABLE_DOCTOR_SKIP_CLI=1` skips the `claude
--version` probe (used by tests to stay fast and offline).

### 4. Install / uninstall / tests / docs

- `install.py`: `copy_into("hooks/fable-doctor.py", ...)` in the hooks step.
- `uninstall.py`: `rm_file` for fable-doctor.py.
- Tests: `looks_complex` end-to-end through the hook (ru prompt with verb+multistep injects once,
  reason `auto`; `FABLE_AUTO=0` silences it; short greeting stays silent; phrase path unaffected);
  doctor against a sandbox home (fresh home → exit 1 with named missing files; faked full install
  → exit 0 with live-fire pass); install/uninstall round-trip includes doctor file; launcher
  syntax checks re-run.
- README: bundle bullets for auto-activation, `--ultra`, `fable doctor`; CHANGELOG Added entries.

## Alternatives considered

- **LLM-scored complexity** (hook calls a model): non-deterministic, adds latency and cost to
  every prompt — rejected; the score heuristic is testable and free.
- **Doctor as a separate repo script** (`scripts/`): rejected — it must ship to the machine it
  diagnoses; ~/.claude/hooks is already the installed-tooling location, and the launcher knows it.
- **Always-inject in every session:** simplest, but burns 12 KB on trivial sessions — rejected;
  scoring keeps the zero-cost-by-default promise.

## Out of scope

- Changing test-after-edit.py (user WIP).
- Auto-update checks, statusline integration, telemetry of any kind.

## Decisions

1. **User-confirmed (2026-07-03):** hybrid auto-activation (heuristic hook + proactive skill
   description) and the full feature set: auto-activation + orchestration + doctor.
2. Taken on the user's behalf: heuristic thresholds (score ≥ 2, weights above) — tuned for
   "obvious tasks trigger, greetings don't"; easy to retune, covered by tests.
3. Taken on the user's behalf: doctor lives in `hooks/` (ships with install), not `scripts/`.
