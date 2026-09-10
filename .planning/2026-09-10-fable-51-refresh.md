# fable-mode: Fable 5.1 refresh + FABLE_CODE.md gap fix

Date: 2026-09-10 · Branch: main · Status: executing · Scope: 11 files · Depends-on: none

## Context
Bundle was authored by Fable 5 (June 2026) when the model was suspended and the only host was Opus 4.8.
Fable 5.1 is now GA. Audit of every shipped file against (a) the live Claude Code harness prompt the
author of this plan is running under and (b) the leaked consumer prompt (bundled copy is byte-identical
to elder-plinius/CL4R1T4S, `diff` exit 0).

## Current state (VERIFIED)
- `shell/fable.zsh:26`, `shell/fable.ps1:39` pin `--model claude-opus-4-8`. README:5,27,46,55,75 say
  "You can't call the model right now". REFUTED live: `claude --model claude-fable-5-1 -p` returns
  harness line "You are powered by the model named Fable 5.1. The exact model ID is claude-fable-5-1."
  (print-mode `modelUsage.canonicalModel` reports `claude-opus-5`; accounting alias, not a fallback,
  because the same probe under `--model claude-opus-5` returns "Opus 5 … knowledge cutoff May 2026").
- `hooks/fable-trigger.py:119` GC glob is `fable-*-` → matches only names ending in "-"; markers are
  `fable-{kind}-{sid}` → GC never prunes. `test_test_after_edit.py:133` covers the OTHER hook only.
- Injectable body of FABLE_CODE.md = 9100 chars vs CAP 9800 (`read_code_rules()` measured).
- FABLE_CODE.md vs live harness prompt, missing: scope discipline ("requested scope is the
  deliverable", concern-then-build, finish-all-else-and-say-what's-left, reaffirm ⇒ proceed, refusal
  style), precise writing rules (~20-word sentences, no em-dash/parenthetical/arrow, numbers+code out
  of prose, header/bold/bullet limits, no closing offer), uncertainty-mid-task ordering, pending-agent
  fabrication ban, they/them default.
- `skills/ground/SKILL.md:56` "never AskUserQuestion" contradicts the harness (blocking decision that
  is genuinely the user's ⇒ AskUserQuestion). 42/42 pytest pass with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1.

## Units of work (verbatim diffs in the commit; acceptance = Done means below)
1. FABLE_CODE.md: rewrite injectable section, add the missing rules, ≤9700 chars, zero em-dashes.
2. shell/fable.zsh, shell/fable.ps1: `FABLE_MODEL` env, default `claude-fable-5-1`.
3. README.md: premise refresh; Opus/Sonnet path via `FABLE_MODEL=claude-opus-4-8 fable`.
4. FABLE_PLAYBOOK.md: header notes host model + that numbers are Fable 5 traces, 5.1 unmeasured.
5. skills/fable/SKILL.md, skills/ground/SKILL.md, agents/grounding-verifier.md: targeted lines.
6. hooks/fable-trigger.py:119 `fable-*-` → `fable-*`; tests: GC test + injectable-size guard.
7. skills/claude-design-patterns/SKILL.md: Claude Artifact CSP note (cdnjs, not unpkg).
8. CHANGELOG.md: Unreleased entries.

## Sequencing
1 → 6 (size test depends on new FABLE_CODE.md) ; 2 → 3 ; rest independent. Verify last.

## Done means
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests` → 0 failed (count ≥ 44).
- `grep -c '—' FABLE_CODE.md` above the divider → 0.
- `grep -n 'claude-opus-4-8' shell/*.zsh shell/*.ps1 README.md` → only in the fallback docs line.
- `python3 hooks/fable-doctor.py` → no FAIL rows.
- `FABLE_MODEL=claude-opus-4-8 fable`-equivalent: `zsh -c 'source shell/fable.zsh; …'` dry-run prints the right model.

## Rollback
`git checkout -- .` before commit; after commit `git revert <sha>`. No installed-machine state changes
until the user re-runs `python3 install.py`.

## Out of scope
Re-measuring the playbook numbers on Fable 5.1 traces; Anthropic upstream skills (mcp-builder,
skill-creator, webapp-testing, explore-data) beyond the one CSP note; docs/before-after.jpg (untracked).
