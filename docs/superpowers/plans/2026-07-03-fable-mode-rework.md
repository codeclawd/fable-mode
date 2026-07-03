# Fable Mode Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make fable-mode activation fire deterministically on every Claude Code version and replace the consumer-prompt payload with a Claude Code-native Fable behavior layer.

**Architecture:** The `fable` launcher declares the mode via `FABLE_MODE=1`, pins `--model claude-opus-4-8`, and appends a new `fable-code.md`; `fable-trigger.py` becomes dual-event (SessionStart injects the playbook when the launcher declared the mode; UserPromptSubmit keeps phrase/effort paths and gains a FABLE_MODE fallback); a new `skills/fable/` skill gives explicit `/fable` activation.

**Tech Stack:** Python ≥ 3.9 stdlib only (hooks, installer, tests via pytest), zsh/bash + PowerShell launchers, Claude Code hooks API (SessionStart, UserPromptSubmit).

## Global Constraints

- Python code must run on 3.9+, stdlib only — no pip dependencies (README promise).
- Hooks must never crash the session: exit 0, silent on any error (existing contract).
- All tests must pass on Windows AND POSIX (CI runs both; no `HOME`-only or `/tmp`-literal assumptions).
- **Commits are deferred:** the working tree carries the user's uncommitted WIP on overlapping files (`shell/*`, `uninstall.py`, `scripts/merge_settings.py`, `README.md`, `CHANGELOG.md`, tests). Run the test cycle per task, but do NOT `git commit`; the user slices commits on return. Commit messages, when they happen, carry no AI attribution (user's global rule).
- Spec: `docs/superpowers/specs/2026-07-03-fable-mode-rework-design.md`.

---

### Task 1: Dual-event `fable-trigger.py`

**Files:**
- Modify: `hooks/fable-trigger.py` (full rewrite below)
- Test: `tests/test_fable_trigger.py`

**Interfaces:**
- Consumes: hook stdin JSON — `hook_event_name`, `source`, `prompt`, `effort`, `session_id`; env `FABLE_MODE`, `CLAUDE_EFFORT`.
- Produces: stdout JSON `{"hookSpecificOutput": {"hookEventName": "<SessionStart|UserPromptSubmit>", "additionalContext": "..."}}`; marker file `fable-loaded-<sid>` in `tempfile.gettempdir()`. Tasks 4–5 register/deregister this script for both events.

- [ ] **Step 1: Extend the test helper and add failing tests**

Replace `tests/test_fable_trigger.py` lines 13–21 (the `run` helper) with:

```python
def run(stdin_obj, home, extra_env=None):
    env = dict(os.environ)
    env["HOME"] = str(home)          # expanduser on POSIX
    env["USERPROFILE"] = str(home)   # expanduser on Windows
    env.pop("CLAUDE_EFFORT", None)   # effort is driven by the payload, not the dev's session
    env.pop("FABLE_MODE", None)      # ditto for the launcher flag
    if extra_env:
        env.update(extra_env)
    p = subprocess.run([sys.executable, str(HOOK)],
                       input=json.dumps(stdin_obj), text=True,
                       capture_output=True, env=env)
    return p.stdout.strip()
```

Append these tests at the end of the file:

```python
def test_sessionstart_with_fable_mode_injects(tmp_path):
    home = make_home(tmp_path)
    out = run({"hook_event_name": "SessionStart", "source": "startup",
               "session_id": str(uuid.uuid4())}, home, extra_env={"FABLE_MODE": "1"})
    assert out, "SessionStart under FABLE_MODE=1 should inject"
    payload = json.loads(out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "SessionStart"
    assert "PLAYBOOK_MARKER_42" in payload["additionalContext"]


def test_sessionstart_without_fable_mode_is_silent(tmp_path):
    home = make_home(tmp_path)
    out = run({"hook_event_name": "SessionStart", "source": "startup",
               "session_id": str(uuid.uuid4())}, home)
    assert out == ""


def test_sessionstart_resume_respects_marker_but_compact_reinjects(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    env = {"FABLE_MODE": "1"}
    first = run({"hook_event_name": "SessionStart", "source": "startup",
                 "session_id": sid}, home, extra_env=env)
    resume = run({"hook_event_name": "SessionStart", "source": "resume",
                  "session_id": sid}, home, extra_env=env)
    compact = run({"hook_event_name": "SessionStart", "source": "compact",
                   "session_id": sid}, home, extra_env=env)
    assert first, "startup should inject"
    assert resume == "", "resume with marker should stay silent"
    assert compact, "compact wiped context, must re-inject"


def test_fable_mode_env_injects_once_on_userpromptsubmit(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    env = {"FABLE_MODE": "1"}
    first = run({"prompt": "hi", "session_id": sid}, home, extra_env=env)
    second = run({"prompt": "hi again", "session_id": sid}, home, extra_env=env)
    assert first, "FABLE_MODE should inject on the first prompt"
    assert second == "", "and stay silent for the rest of the session"


def test_sessionstart_marker_suppresses_userpromptsubmit_repeat(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    env = {"FABLE_MODE": "1"}
    ss = run({"hook_event_name": "SessionStart", "source": "startup",
              "session_id": sid}, home, extra_env=env)
    ups = run({"prompt": "hello", "session_id": sid}, home, extra_env=env)
    assert ss, "SessionStart injects"
    assert ups == "", "UserPromptSubmit must not double-inject the same session"


def test_effort_level_dict_payload_injects(tmp_path):
    home = make_home(tmp_path)
    out = run({"prompt": "hi", "effort": {"level": "xhigh"},
               "session_id": str(uuid.uuid4())}, home)
    assert out, "effort.level dict form (documented payload) should inject"
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python -m pytest tests/test_fable_trigger.py -v`
Expected: the 5 pre-existing tests PASS; `test_sessionstart_with_fable_mode_injects`, `test_sessionstart_resume_respects_marker_but_compact_reinjects`, `test_fable_mode_env_injects_once_on_userpromptsubmit`, `test_sessionstart_marker_suppresses_userpromptsubmit_repeat` FAIL (empty output — old script has no SessionStart branch and ignores FABLE_MODE). `test_sessionstart_without_fable_mode_is_silent` and `test_effort_level_dict_payload_injects` may already pass — that's fine.

- [ ] **Step 3: Rewrite `hooks/fable-trigger.py`**

Full replacement content:

```python
#!/usr/bin/env python3
"""Dual-event hook: load the Fable execution playbook when the mode is active.

SessionStart      When the `fable` launcher declared the mode (FABLE_MODE=1):
                  sources startup/clear/compact always inject (fresh or wiped
                  context); resume injects only if this session has no marker
                  yet. This path works on every Claude Code version — it does
                  not depend on the harness exposing effort to hooks.
UserPromptSubmit  A trigger phrase ("use fable" / "fable mode" / "load fable")
                  always injects (explicit intent; re-say after a compaction).
                  Heavy effort (payload effort.level, else CLAUDE_EFFORT env)
                  or FABLE_MODE injects once per session (marker file keyed by
                  session_id) so the ~12 KB playbook isn't re-sent every prompt.

No trigger -> prints nothing -> the playbook costs zero tokens by default.
"""
import sys
import json
import re
import os
import tempfile

PLAYBOOK = os.path.expanduser(os.path.join("~", ".claude", "FABLE_PLAYBOOK.md"))
TRIGGER = re.compile(r"\b(use fable|fable mode|load fable)\b", re.I)
HEAVY_EFFORT = {"xhigh", "max", "ultracode"}


def active_effort(data):
    """Effort from the hook JSON (effort.level or effort string), else env."""
    eff = data.get("effort")
    if isinstance(eff, dict):
        eff = eff.get("level")
    if not eff:
        eff = os.environ.get("CLAUDE_EFFORT", "")
    return str(eff).strip().lower()


def fable_mode():
    return os.environ.get("FABLE_MODE", "").strip() == "1"


def marker_path(data):
    sid = str(data.get("session_id") or "nosession")
    sid = re.sub(r"[^A-Za-z0-9_-]", "_", sid)
    return os.path.join(tempfile.gettempdir(), "fable-loaded-" + sid)


def write_marker(path):
    try:
        open(path, "w").close()
    except Exception:
        pass  # marker is best-effort; worst case is one duplicate injection


def inject(event, why):
    try:
        with open(PLAYBOOK, encoding="utf-8") as f:
            body = f.read()
    except Exception:
        return  # playbook missing/unreadable: never block the session
    context = ("Fable mode active ({}). Adopt the execution playbook below as "
               "standing discipline for the rest of this session:\n\n".format(why)
               + body)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        }
    }))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # malformed input: never block the prompt

    event = str(data.get("hook_event_name") or "UserPromptSubmit")
    marker = marker_path(data)

    if event == "SessionStart":
        if not fable_mode():
            return
        source = str(data.get("source") or "startup").lower()
        if source == "resume" and os.path.exists(marker):
            return  # context usually survives a resume; don't double-inject
        write_marker(marker)
        inject("SessionStart", "launcher")
        return

    prompt = data.get("prompt", "") or ""
    phrase = bool(TRIGGER.search(prompt))
    effort = active_effort(data)
    heavy = effort in HEAVY_EFFORT or fable_mode()

    if not (phrase or heavy):
        return

    # Heavy-only trigger: inject just once per session.
    if heavy and not phrase:
        if os.path.exists(marker):
            return
        write_marker(marker)

    if phrase:
        why = "phrase"
    elif effort in HEAVY_EFFORT:
        why = "effort=" + effort
    else:
        why = "launcher"
    inject("UserPromptSubmit", why)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the full test file**

Run: `python -m pytest tests/test_fable_trigger.py -v`
Expected: all 11 tests PASS.

- [ ] **Step 5: Manual smoke check (Windows host)**

Run: `echo {"hook_event_name":"SessionStart","source":"startup","session_id":"smoke-1"} | python hooks/fable-trigger.py` with `FABLE_MODE=1` set, from the repo root, HOME untouched (real playbook installed).
Expected: JSON with `"hookEventName": "SessionStart"` and the real playbook text. Delete the `fable-loaded-smoke-1` marker from `%TEMP%` afterwards.

---

### Task 2: `fable-code.md` + `skills/fable/SKILL.md`

**Files:**
- Create: `fable-code.md` (repo root, sibling of `fable-system.md`)
- Create: `skills/fable/SKILL.md`

**Interfaces:**
- Produces: `fable-code.md` consumed by the launchers (Task 3, `--append-system-prompt-file`) and copied by `install.py` (Task 4); `skills/fable/` is picked up automatically by `install.py`'s existing skills loop and by `uninstall.py`'s `bundled_skill_names()`.

- [ ] **Step 1: Write `fable-code.md`**

Full content:

```markdown
# Fable — Claude Code behavior layer

Provenance: an original distillation of first-party Claude Fable 5 behavior
observed in Claude Code (2026-07). Not the leaked consumer prompt — that file
(`fable-system.md`) describes a chat tab; this one describes how Fable operates
in a terminal harness. Adopt everything below as standing discipline.

## The final message is the deliverable

Text between tool calls may never be shown; everything the user needs from a
turn — answers, findings, conclusions — must be in the last message, with no
tool calls after it. If something important surfaced mid-turn, restate it there.
Lead with the outcome: the first sentence answers "what happened" or "what did
you find"; supporting detail and reasoning come after, for readers who want them.

## Readable beats concise

Shorten by selecting what matters, not by compressing prose into fragments.
Complete sentences; technical terms spelled out; no arrow chains ("A → B →
fails"); no shorthand or codenames the reader must reverse-engineer; explain in
place instead of referencing labels or numbering invented earlier in the turn.
If the reader has to reread or ask a follow-up, the brevity saved nothing.
Simple questions get plain prose — no headers, no sections. Tables only for
short enumerable facts, explained in surrounding prose, not in the cells.

## Working rhythm

One sentence on intent before the first tool call. Surface load-bearing
findings and direction changes the moment they happen — one line each.
Otherwise, no narration between tool calls: no "Let me…", no result recaps, no
progress theater. Several tool calls in a row with no prose between them is
correct, not rude.

## Tool discipline

Batch independent tool calls in a single block; keep strict sequencing only
where a step consumes the previous result. Prefer structured tools (Grep, Glob,
Read) over shell pipelines; reference code as `file:line`. Read the exact
region you are about to edit, in this session, immediately before editing —
and your own successful edit invalidates your last read of that file. Absolute
paths, not `cd`.

## Code and comments

Write code that reads like the surrounding code — match its comment density,
naming, and idiom. A comment states only a constraint the code cannot show.
Never write comments that narrate the change, justify it to a reviewer, or say
where it came from; that is noise the moment the change lands.

## Autonomy, honesty, and stopping

Proceed without asking on reversible actions that follow from the request.
Stop and ask only for destructive actions, outward-facing effects (sending,
publishing), or genuine scope changes. Before deleting or overwriting, look at
the target; if it contradicts its description or you didn't create it, surface
that instead of proceeding. Report outcomes faithfully: failing tests are shown
with their output, skipped steps are named as skipped, and "done" is said only
after verification — an unverified edit is an untrue "done".

When the user is describing a problem or thinking out loud, the deliverable is
your assessment: report findings and stop; don't apply a fix until asked.

## The end-of-turn rule

Before ending a turn, check the last paragraph. If it is a plan, a list of next
steps, a question a tool could answer, or a promise about work not yet done
("I'll…"), do that work now instead of ending the turn. End only when the task
is complete or blocked on input only the user can provide.
```

- [ ] **Step 2: Write `skills/fable/SKILL.md`**

Full content:

```markdown
---
name: fable
description: Activate Fable mode - adopt the Fable execution playbook and the Claude Code behavior layer as standing discipline for this session. Use when the user types /fable, says "fable mode", "use fable", "work like fable", or asks for maximum-discipline execution.
---

# Fable mode

Activate the full Fable discipline for the rest of this session:

1. Read `~/.claude/FABLE_PLAYBOOK.md` (execution discipline: reason before
   acting, observe-then-decide, verify every edit, communication floor,
   grounding protocol). If the file is missing, read `FABLE_PLAYBOOK.md` from
   this skill's repository instead.
2. Read `~/.claude/fable-code.md` (the Claude Code behavior layer: final-message
   contract, readable-over-concise, tool discipline, autonomy and honesty
   rules). Same fallback.
3. Adopt both as standing discipline — they govern every subsequent turn of
   this session, not just the next reply.
4. Confirm activation in one line ("Fable mode active — playbook and behavior
   layer loaded."), then continue with the user's task. Do not summarize the
   documents back.

Scale the heavier machinery to the task: the evidence ledger and the
`grounding-verifier` agent are for non-trivial or hard-to-reverse work, not for
typo fixes (the playbook's own calibration rules apply).
```

- [ ] **Step 3: Sanity-check formats**

Run: `python -c "import pathlib; t = pathlib.Path('skills/fable/SKILL.md').read_text(encoding='utf-8'); assert t.startswith('---') and 'name: fable' in t and 'description:' in t; print('frontmatter ok')"`
Expected: `frontmatter ok`

---

### Task 3: Launchers pin the model and declare the mode

**Files:**
- Modify: `shell/fable.zsh` (full replacement)
- Modify: `shell/fable.ps1` (full replacement)

**Interfaces:**
- Consumes: `~/.claude/fable-code.md` (Task 2, copied by Task 4's installer).
- Produces: env `FABLE_MODE=1` for the `claude` process tree (consumed by `fable-trigger.py`, Task 1).

- [ ] **Step 1: Replace `shell/fable.zsh`**

```zsh
# Fable mode launcher. Add to ~/.zshrc, or: `source ~/path/to/fable-mode/shell/fable.zsh`
#
# Launches Claude Code pinned to Opus 4.8 with the Fable Claude-Code behavior
# layer appended and xhigh effort, and declares the mode via FABLE_MODE=1 so
# fable-trigger.py injects the execution playbook at SessionStart — reliable on
# every Claude Code version, not only those that expose effort to hooks.
#
# install.py copies fable-code.md into ~/.claude for you.
# Want multi-agent auto-orchestration too? Add: --settings '{"ultracode": true}'
fable() {
  FABLE_MODE=1 claude --model claude-opus-4-8 \
    --append-system-prompt-file "$HOME/.claude/fable-code.md" \
    --effort xhigh "$@"
}
```

- [ ] **Step 2: Replace `shell/fable.ps1`**

```powershell
# Fable mode launcher (PowerShell). Dot-source from your profile, or:
#   . C:\path\to\fable-mode\shell\fable.ps1
#
# Launches Claude Code pinned to Opus 4.8 with the Fable Claude-Code behavior
# layer appended and xhigh effort, and declares the mode via FABLE_MODE=1 so
# fable-trigger.py injects the execution playbook at SessionStart — reliable on
# every Claude Code version, not only those that expose effort to hooks.
#
# install.ps1 copies fable-code.md into ~\.claude for you.
# Want multi-agent auto-orchestration too? Add: --settings '{"ultracode": true}'
function fable {
    $env:FABLE_MODE = "1"
    try {
        claude --model claude-opus-4-8 `
            --append-system-prompt-file "$HOME\.claude\fable-code.md" `
            --effort xhigh @args
    }
    finally {
        Remove-Item Env:FABLE_MODE -ErrorAction SilentlyContinue
    }
}
```

- [ ] **Step 3: Syntax-check both**

Run: `bash -n shell/fable.zsh`
Expected: no output, exit 0.
Run: `pwsh -NoProfile -Command ". ./shell/fable.ps1; if (Get-Command fable -ErrorAction SilentlyContinue) { 'ps1 ok' } else { exit 1 }"`
Expected: `ps1 ok`

---

### Task 4: Installer wiring (merge_settings, fragment, install.py, install tests)

**Files:**
- Modify: `scripts/merge_settings.py:44-50` (add SessionStart ensure)
- Modify: `settings.fragment.json`
- Modify: `install.py:98-102` (copy fable-code.md)
- Test: `tests/test_install.py`

**Interfaces:**
- Consumes: `fable-code.md`, `skills/fable/` (Task 2 — the skills loop copies any `skills/*` dir automatically).
- Produces: `~/.claude/settings.json` with a `SessionStart` entry whose command contains `fable-trigger.py`; `~/.claude/fable-code.md`; `~/.claude/skills/fable/SKILL.md`. Task 5's uninstaller must reverse exactly these.

- [ ] **Step 1: Add failing assertions to `tests/test_install.py`**

In `test_install_copies_everything`, after the existing `assert (claude / "fable-system.md").is_file()` line, add:

```python
    assert (claude / "fable-code.md").is_file()
    assert (claude / "skills" / "fable" / "SKILL.md").is_file()
```

and after the existing `cmd = ...` / `assert sys.executable in cmd` lines, add:

```python
    ss_cmd = s["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "fable-trigger.py" in ss_cmd
```

In `test_install_is_idempotent`, after `assert len(s["hooks"]["PostToolUse"]) == 1`, add:

```python
    assert len(s["hooks"]["SessionStart"]) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_install.py -v`
Expected: both modified tests FAIL (`fable-code.md` missing, `KeyError: 'SessionStart'`).

- [ ] **Step 3: Implement**

`scripts/merge_settings.py` — after the existing `ensure("UserPromptSubmit", ...)` call, add:

```python
    ensure("SessionStart",
           {"hooks": [{"type": "command", "command": cmd("fable-trigger.py")}]},
           "fable-trigger.py")
```

`settings.fragment.json` — full replacement:

```json
{
  "_comment": "Reference only. install.py merges these into ~/.claude/settings.json (with a backup) and writes ABSOLUTE interpreter + script paths so the hooks work without $HOME/python3 resolution. If editing by hand, replace 'python3' with your interpreter (e.g. 'python' on Windows) and $HOME with the full path to your home dir.",
  "alwaysThinkingEnabled": true,
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "python3 $HOME/.claude/hooks/fable-trigger.py" }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "python3 $HOME/.claude/hooks/fable-trigger.py" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command", "command": "python3 $HOME/.claude/hooks/test-after-edit.py" }
        ]
      }
    ]
  }
}
```

`install.py` — after the `print("-> fable system prompt")` / `copy_into("fable-system.md", CLAUDE)` pair, add:

```python
    print("-> fable behavior layer (Claude Code)")
    copy_into("fable-code.md", CLAUDE)
```

- [ ] **Step 4: Run install tests**

Run: `python -m pytest tests/test_install.py -v`
Expected: all tests PASS (3 tests).

---

### Task 5: Uninstaller wiring + round-trip test

**Files:**
- Modify: `uninstall.py:106,133-136`
- Test: Create `tests/test_uninstall.py`

**Interfaces:**
- Consumes: the installed layout produced by `install.py` (Task 4).
- Produces: clean `~/.claude` — no `fable-code.md`, no `skills/fable/`, no `SessionStart`/`UserPromptSubmit`/`PostToolUse` entries referencing fable scripts; foreign hooks preserved.

- [ ] **Step 1: Write failing round-trip test `tests/test_uninstall.py`**

```python
"""Round-trip test: install into a sandbox home, uninstall, verify clean state."""
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, REPO / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sandbox(mod, tmp_path, windows=True):
    mod.HOME = str(tmp_path)
    mod.CLAUDE = str(tmp_path / ".claude")
    mod.IS_WINDOWS = windows
    mod.powershell_profile_path = lambda: str(tmp_path / "profile.ps1")
    return mod


def test_uninstall_reverses_install(tmp_path):
    inst = sandbox(load("fable_install", "install.py"), tmp_path)
    uninst = sandbox(load("fable_uninstall", "uninstall.py"), tmp_path)
    inst.main()

    claude = tmp_path / ".claude"
    # plant a foreign hook that must survive
    s = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    s["hooks"]["SessionStart"].append(
        {"hooks": [{"type": "command", "command": "node keepme.cjs"}]})
    (claude / "settings.json").write_text(json.dumps(s, indent=2), encoding="utf-8")

    uninst.main()

    assert not (claude / "FABLE_PLAYBOOK.md").exists()
    assert not (claude / "fable-system.md").exists()
    assert not (claude / "fable-code.md").exists()
    assert not (claude / "hooks" / "fable-trigger.py").exists()
    assert not (claude / "skills" / "fable").exists()
    assert not (claude / "skills" / "ground").exists()
    assert "fable.ps1" not in (tmp_path / "profile.ps1").read_text(encoding="utf-8")

    s = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    ss = s["hooks"]["SessionStart"]
    assert len(ss) == 1 and "keepme.cjs" in ss[0]["hooks"][0]["command"]
    assert "UserPromptSubmit" not in s["hooks"]
    assert "PostToolUse" not in s["hooks"]
    assert s["alwaysThinkingEnabled"] is True
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_uninstall.py -v`
Expected: FAIL — `fable-code.md` still present and the fable `SessionStart` entry survives (uninstaller doesn't know either yet).

- [ ] **Step 3: Implement in `uninstall.py`**

In `clean_settings()`, change the event loop line

```python
    for event in ("UserPromptSubmit", "PostToolUse"):
```

to

```python
    for event in ("SessionStart", "UserPromptSubmit", "PostToolUse"):
```

In `main()`, after `rm_file(os.path.join(CLAUDE, "fable-system.md"))`, add:

```python
    rm_file(os.path.join(CLAUDE, "fable-code.md"))
```

- [ ] **Step 4: Run the round-trip test**

Run: `python -m pytest tests/test_uninstall.py -v`
Expected: PASS.

---

### Task 6: Playbook amendment + docs

**Files:**
- Modify: `FABLE_PLAYBOOK.md` (add one subsection at the end of "How Fable talks")
- Modify: `README.md` (bundle list, launcher description)
- Modify: `CHANGELOG.md` (Unreleased entries)

**Interfaces:**
- Consumes: terminology from Tasks 1–3 (`FABLE_MODE`, SessionStart injection, `fable-code.md`).

- [ ] **Step 1: Amend `FABLE_PLAYBOOK.md`**

Insert immediately before the `## Grounding — prove it before you call it done` heading:

```markdown
### The Claude Code layer (first-party, 2026-07)

Observed first-party Fable 5 behavior in Claude Code adds three corrections to
the voice layer above — adopt them with the same weight:

- **The final message is the deliverable.** Mid-turn text may never be shown;
  answers, findings, and conclusions must all appear in the turn's last
  message, outcome first. A perfect investigation with a buried conclusion
  reads as no conclusion.
- **Readable beats concise.** Shorten by selecting what matters, not by
  compressing prose into fragments, arrow chains ("A → B → fails"), or
  shorthand the reader must reverse-engineer. Complete sentences; explain in
  place. If the reader must reread or ask a follow-up, the brevity saved
  nothing.
- **Assessment mode.** When the user is describing a problem or thinking out
  loud rather than requesting a change, the deliverable is the assessment:
  report findings and stop; don't apply the fix until asked.
```

- [ ] **Step 2: Update `README.md`**

In "What's in the bundle", replace the launcher bullet

```markdown
- **`fable` launcher** — Opus 4.8 + the prompt + `xhigh` effort (`fable.zsh` for Unix shells, `fable.ps1` for PowerShell). Want multi-agent auto-orchestration on top? Swap `--effort xhigh` for `--settings '{"ultracode": true}'` in the launcher.
```

with

```markdown
- **`fable` launcher** — pins `--model claude-opus-4-8`, appends `fable-code.md`, sets `xhigh` effort, and declares the mode via `FABLE_MODE=1` so the playbook injects at session start on every Claude Code version (`fable.zsh` for Unix shells, `fable.ps1` for PowerShell). Want multi-agent auto-orchestration on top? Add `--settings '{"ultracode": true}'`.
```

and add two bullets after the `fable-system.md` bullet:

```markdown
- **`fable-code.md`** — an original Claude Code-native distillation of Fable's terminal behavior (final-message contract, readable-over-concise, tool discipline, autonomy rules). This is what the launcher actually appends; the consumer prompt above stays bundled for reference.
- **`/fable` skill** — explicit activation: reads the playbook + behavior layer and adopts both mid-session, no launcher required.
```

- [ ] **Step 3: Update `CHANGELOG.md`**

Under `## [Unreleased]` → `### Fixed`, add as the first bullet:

```markdown
- The playbook injector never actually fired: the effort path needs `effort` in
  the hook payload or `CLAUDE_EFFORT` in the hook environment, which Claude Code
  ≤ 2.1.198 did not provide, and the trigger phrases were undiscoverable. The
  launcher now declares the mode via `FABLE_MODE=1` and `fable-trigger.py`
  became dual-event — SessionStart injection (version-independent) plus the old
  phrase/effort paths and a `FABLE_MODE` fallback on UserPromptSubmit.
```

Under `### Added`, add:

```markdown
- `fable-code.md`: an original Claude Code-native Fable behavior layer; the
  launcher appends it instead of the 1,600-line consumer prompt (which stays
  bundled for reference).
- `/fable` skill for explicit mid-session activation.
- The launcher pins `--model claude-opus-4-8`, making the README's "runs on
  Opus 4.8" promise true regardless of the user's default model.
- Round-trip uninstall test (`tests/test_uninstall.py`).
```

- [ ] **Step 4: Full suite + smoke**

Run: `python -m pytest -q`
Expected: all tests PASS (existing 4 files + new uninstall file; the WIP `test_test_after_edit.py` suite must stay green too).

---

## Self-Review Notes

- Spec coverage: §1→Task 3, §2→Task 1, §3→Task 2, §4→Task 2, §5→Task 6, §6→Tasks 4–6. No gaps.
- `install.py` needs no skills-loop change for `skills/fable/` (existing loop copies every dir); `uninstall.py` needs no change for it either (`bundled_skill_names()` enumerates the repo). Verified against current sources.
- Type/name consistency: `FABLE_MODE`, `fable-code.md`, `fable-loaded-<sid>` markers, `ensure("SessionStart", ...)` used identically across tasks.
