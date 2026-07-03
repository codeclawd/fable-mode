# Fable Auto-Activation, Orchestration & Doctor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complex prompts activate Fable mode by themselves in any session; `fable --ultra` enables ultracode orchestration; `fable doctor` verifies the whole install/activation chain.

**Architecture:** A score-based `looks_complex()` heuristic joins the existing "heavy" sources in `fable-trigger.py`'s UserPromptSubmit branch (once-per-session, `FABLE_AUTO=0` opt-out); the `/fable` skill description gains a proactive clause; both launchers get first-argument dispatch for `doctor` and `--ultra`; a new stdlib-only `hooks/fable-doctor.py` runs presence/settings/version/live-fire/evidence checks.

**Tech Stack:** Python ≥ 3.9 stdlib only, pytest, zsh/bash + PowerShell.

## Global Constraints

- Python 3.9+, stdlib only, no pip installs (README promise).
- Hooks never crash the session: exit 0, silent on error.
- Tests must pass on Windows AND POSIX.
- **Commits are deferred** — user WIP is intermixed in the working tree; the user slices commits. No AI attribution in any eventual commit message (user's global rule).
- Spec: `docs/superpowers/specs/2026-07-03-fable-auto-orchestration-design.md`.

---

### Task 1: Complexity heuristic in `fable-trigger.py`

**Files:**
- Modify: `hooks/fable-trigger.py`
- Test: `tests/test_fable_trigger.py`

**Interfaces:**
- Produces: `looks_complex(prompt) -> bool` (score ≥ 2); env knob `FABLE_AUTO` ("0" disables); injection reason string `auto`. Task 4's doctor and Task 6's docs reference `FABLE_AUTO=0`.

- [ ] **Step 1: Add failing tests**

In `tests/test_fable_trigger.py`, update the `run` helper to also pop `FABLE_AUTO`:

```python
    env.pop("FABLE_MODE", None)      # ditto for the launcher flag
    env.pop("FABLE_AUTO", None)      # and the auto-heuristic knob
```

Append at the end of the file:

```python
def test_complex_prompt_auto_injects_once(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    prompt = "Сделай рефакторинг hooks/fable-trigger.py и добавь тесты, затем обнови README"
    first = run({"prompt": prompt, "session_id": sid}, home)
    second = run({"prompt": prompt, "session_id": sid}, home)
    assert first, "task-shaped prompt should auto-inject"
    ctx = json.loads(first)["hookSpecificOutput"]["additionalContext"]
    assert "Fable mode active (auto)" in ctx
    assert second == "", "auto path is once per session"


def test_fable_auto_opt_out(tmp_path):
    home = make_home(tmp_path)
    prompt = "Implement a REST endpoint in api/server.py and fix the failing tests"
    out = run({"prompt": prompt, "session_id": str(uuid.uuid4())}, home,
              extra_env={"FABLE_AUTO": "0"})
    assert out == "", "FABLE_AUTO=0 must disable the heuristic"


def test_simple_greeting_stays_silent(tmp_path):
    home = make_home(tmp_path)
    assert run({"prompt": "привет, как дела?",
                "session_id": str(uuid.uuid4())}, home) == ""
    assert run({"prompt": "what time is it",
                "session_id": str(uuid.uuid4())}, home) == ""
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_fable_trigger.py -v`
Expected: `test_complex_prompt_auto_injects_once` FAILS (empty output); the two guard tests PASS already; all pre-existing tests PASS.

- [ ] **Step 3: Implement the heuristic**

In `hooks/fable-trigger.py`, after the `HEAVY_EFFORT` constant, add:

```python
# Auto-activation heuristic: score-based guess that a prompt is a real
# engineering task. >= 2 points = complex. Disable with FABLE_AUTO=0.
TASK_VERBS = re.compile(
    r"\b(implement|refactor|migrat\w*|build|creat\w*|add|fix|debug|integrat\w*|"
    r"optimi[sz]\w*|rewrit\w*|design|install|set up"
    r"|сдела\w*|добав\w*|почин\w*|исправ\w*|реализу\w*|перепиш\w*|настро\w*|"
    r"созда\w*|собер\w*|интегрир\w*|оптимизир\w*|мигрир\w*|разработ\w*)", re.I)
MULTISTEP = re.compile(r"\b(затем|потом|после этого|then|steps?)\b|^\s*\d+[.)]\s",
                       re.I | re.M)
PATHISH = re.compile(
    r"\w+\.(py|js|ts|tsx|java|go|rs|c|cpp|h|cs|rb|php|md|json|ya?ml|toml|ps1|sh|zsh)\b"
    r"|[/\\][\w.-]+[/\\]")
FENCE_OR_TRACE = re.compile(r"```|Traceback \(most recent call last\)|^\s*File \"",
                            re.M)


def looks_complex(prompt):
    score = 0
    if len(prompt) >= 400:
        score += 2
    if FENCE_OR_TRACE.search(prompt):
        score += 2
    score += min(len(set(m.group(0).lower() for m in TASK_VERBS.finditer(prompt))), 2)
    if PATHISH.search(prompt):
        score += 1
    if MULTISTEP.search(prompt):
        score += 1
    if len([ln for ln in prompt.splitlines() if ln.strip()]) >= 3:
        score += 1
    return score >= 2
```

In `main()`, replace the block from `phrase = bool(TRIGGER.search(prompt))` through the final `inject(...)` call with:

```python
    phrase = bool(TRIGGER.search(prompt))
    effort = active_effort(data)
    auto = os.environ.get("FABLE_AUTO", "").strip() != "0" and looks_complex(prompt)
    heavy = effort in HEAVY_EFFORT or fable_mode() or auto

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
    elif fable_mode():
        why = "launcher"
    else:
        why = "auto"
    inject("UserPromptSubmit", why)
```

Also update the module docstring's UserPromptSubmit paragraph to mention the auto path:

```
UserPromptSubmit  A trigger phrase ("use fable" / "fable mode" / "load fable")
                  always injects (explicit intent; re-say after a compaction).
                  Heavy effort (payload effort.level, else CLAUDE_EFFORT env),
                  FABLE_MODE, or a task-shaped prompt (looks_complex heuristic;
                  disable with FABLE_AUTO=0) injects once per session (marker
                  file keyed by session_id).
```

- [ ] **Step 4: Run the full trigger suite**

Run: `python -m pytest tests/test_fable_trigger.py -v`
Expected: all 14 tests PASS.

---

### Task 2: Proactive `/fable` skill

**Files:**
- Modify: `skills/fable/SKILL.md`

**Interfaces:**
- Consumes: nothing new. Produces: skill description used verbatim by Task 6's README bullet.

- [ ] **Step 1: Update frontmatter description**

Replace the `description:` line with:

```yaml
description: Activate Fable mode - adopt the Fable execution playbook and the Claude Code behavior layer as standing discipline for this session. Use when the user types /fable, says "fable mode", "use fable", "work like fable", or asks for maximum-discipline execution - and PROACTIVELY at the start of any non-trivial engineering task (multi-step implementation, refactor, migration, long debugging session) when the playbook is not already in context.
```

- [ ] **Step 2: Add the already-loaded shortcut to the body**

Insert after the numbered list (before "Scale the heavier machinery"):

```markdown
If the playbook is already in this context (look for a "Fable mode active"
injection from the hook), skip the reads: confirm activation in one line and
apply `fable-code.md` from context, reading it only if absent.
```

- [ ] **Step 3: Verify frontmatter still parses**

Run: `python -c "import pathlib; t = pathlib.Path('skills/fable/SKILL.md').read_text(encoding='utf-8'); assert t.startswith('---') and 'PROACTIVELY' in t; print('frontmatter ok')"`
Expected: `frontmatter ok`

---

### Task 3: Launcher dispatch — `doctor` and `--ultra`

**Files:**
- Modify: `shell/fable.zsh` (full replacement)
- Modify: `shell/fable.ps1` (full replacement)

**Interfaces:**
- Consumes: `~/.claude/hooks/fable-doctor.py` (created in Task 4; the launcher only references the path).
- Produces: `fable doctor [...]` and `fable --ultra|-u [...]` in both shells.

- [ ] **Step 1: Replace `shell/fable.zsh`**

```zsh
# Fable mode launcher. Add to ~/.zshrc, or: `source ~/path/to/fable-mode/shell/fable.zsh`
#
# `fable`          Claude Code pinned to Opus 4.8, Fable Claude-Code behavior
#                  layer appended, xhigh effort, FABLE_MODE=1 declared so
#                  fable-trigger.py injects the playbook at SessionStart.
# `fable --ultra`  Same, plus ultracode: the harness auto-runs multi-agent
#                  workflows for substantive tasks (heavy on tokens).
# `fable doctor`   Verify the whole install/activation chain mechanically.
#
# install.py copies fable-code.md and fable-doctor.py into ~/.claude for you.
fable() {
  if [[ "$1" == "doctor" ]]; then
    shift
    python3 "$HOME/.claude/hooks/fable-doctor.py" "$@"
    return
  fi
  local -a extra
  if [[ "$1" == "--ultra" || "$1" == "-u" ]]; then
    shift
    extra=(--settings '{"ultracode": true}')
  fi
  FABLE_MODE=1 claude --model claude-opus-4-8 \
    --append-system-prompt-file "$HOME/.claude/fable-code.md" \
    --effort xhigh "${extra[@]}" "$@"
}
```

- [ ] **Step 2: Replace `shell/fable.ps1`**

```powershell
# Fable mode launcher (PowerShell). Dot-source from your profile, or:
#   . C:\path\to\fable-mode\shell\fable.ps1
#
# `fable`          Claude Code pinned to Opus 4.8, Fable Claude-Code behavior
#                  layer appended, xhigh effort, FABLE_MODE=1 declared so
#                  fable-trigger.py injects the playbook at SessionStart.
# `fable --ultra`  Same, plus ultracode: the harness auto-runs multi-agent
#                  workflows for substantive tasks (heavy on tokens).
# `fable doctor`   Verify the whole install/activation chain mechanically.
#
# install.ps1 copies fable-code.md and fable-doctor.py into ~\.claude for you.
function fable {
    $rest = @($args)
    if ($rest.Count -gt 0 -and $rest[0] -eq 'doctor') {
        & python "$HOME\.claude\hooks\fable-doctor.py" @($rest | Select-Object -Skip 1)
        return
    }
    $extra = @()
    if ($rest.Count -gt 0 -and ($rest[0] -eq '--ultra' -or $rest[0] -eq '-u')) {
        $rest = @($rest | Select-Object -Skip 1)
        $extra = @('--settings', '{"ultracode": true}')
    }
    $env:FABLE_MODE = "1"
    try {
        claude --model claude-opus-4-8 `
            --append-system-prompt-file "$HOME\.claude\fable-code.md" `
            --effort xhigh @extra @rest
    }
    finally {
        Remove-Item Env:FABLE_MODE -ErrorAction SilentlyContinue
    }
}
```

- [ ] **Step 3: Syntax-check both**

Run: `bash -n shell/fable.zsh && echo "zsh ok"`
Expected: `zsh ok`
Run (PowerShell): `. ./shell/fable.ps1; if (Get-Command fable -ErrorAction SilentlyContinue) { 'ps1 ok' } else { exit 1 }`
Expected: `ps1 ok`

---

### Task 4: `hooks/fable-doctor.py`

**Files:**
- Create: `hooks/fable-doctor.py`
- Test: Create `tests/test_fable_doctor.py`

**Interfaces:**
- Consumes: the installed layout under `~/.claude` (resolved via `HOME`/`USERPROFILE` at runtime) and `hooks/fable-trigger.py`'s stdin/stdout contract from Task 1.
- Produces: exit 0 = healthy (warnings allowed), exit 1 = hard failure; env knob `FABLE_DOCTOR_SKIP_CLI=1` skips the `claude --version` probe. Task 5 installs/uninstalls this file; Task 3's launchers invoke it.

- [ ] **Step 1: Write failing tests `tests/test_fable_doctor.py`**

```python
"""Tests for hooks/fable-doctor.py — the install/activation chain checker."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCTOR = REPO / "hooks" / "fable-doctor.py"


def run_doctor(home):
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["FABLE_DOCTOR_SKIP_CLI"] = "1"   # offline + fast in CI
    env.pop("CLAUDE_EFFORT", None)
    env.pop("FABLE_MODE", None)
    return subprocess.run([sys.executable, str(DOCTOR)], capture_output=True,
                          text=True, env=env)


def fake_install(home):
    claude = home / ".claude"
    (claude / "hooks").mkdir(parents=True)
    (claude / "skills" / "fable").mkdir(parents=True)
    (claude / "agents").mkdir(parents=True)
    for rel in ("FABLE_PLAYBOOK.md", "fable-code.md", "fable-system.md"):
        (claude / rel).write_text("PLAYBOOK", encoding="utf-8")
    shutil.copy(REPO / "hooks" / "fable-trigger.py",
                claude / "hooks" / "fable-trigger.py")
    (claude / "hooks" / "test-after-edit.py").write_text("# stub", encoding="utf-8")
    (claude / "hooks" / "fable-doctor.py").write_text("# stub", encoding="utf-8")
    (claude / "skills" / "fable" / "SKILL.md").write_text("---\nname: fable\n---",
                                                          encoding="utf-8")
    (claude / "agents" / "grounding-verifier.md").write_text("x", encoding="utf-8")
    trigger = str(claude / "hooks" / "fable-trigger.py")
    tester = str(claude / "hooks" / "test-after-edit.py")
    settings = {
        "alwaysThinkingEnabled": True,
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command",
                                         "command": '"{}" "{}"'.format(sys.executable, trigger)}]}],
            "UserPromptSubmit": [{"hooks": [{"type": "command",
                                             "command": '"{}" "{}"'.format(sys.executable, trigger)}]}],
            "PostToolUse": [{"matcher": "Edit|Write|MultiEdit",
                             "hooks": [{"type": "command",
                                        "command": '"{}" "{}"'.format(sys.executable, tester)}]}],
        },
    }
    (claude / "settings.json").write_text(json.dumps(settings), encoding="utf-8")


def test_fresh_home_fails_with_named_missing_files(tmp_path):
    p = run_doctor(tmp_path)
    assert p.returncode == 1
    assert "missing" in p.stdout
    assert "FABLE_PLAYBOOK.md" in p.stdout


def test_healthy_install_passes_live_fire(tmp_path):
    fake_install(tmp_path)
    p = run_doctor(tmp_path)
    assert "live fire: SessionStart injects" in p.stdout, p.stdout
    assert "live fire: UserPromptSubmit phrase injects" in p.stdout, p.stdout
    assert p.returncode == 0, p.stdout


def test_unregistered_hook_is_a_hard_failure(tmp_path):
    fake_install(tmp_path)
    claude = tmp_path / ".claude"
    s = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    del s["hooks"]["SessionStart"]
    (claude / "settings.json").write_text(json.dumps(s), encoding="utf-8")
    p = run_doctor(tmp_path)
    assert p.returncode == 1
    assert "not registered for SessionStart" in p.stdout
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_fable_doctor.py -v`
Expected: all 3 tests FAIL/ERROR (`hooks/fable-doctor.py` does not exist).

- [ ] **Step 3: Write `hooks/fable-doctor.py`**

```python
#!/usr/bin/env python3
"""fable doctor: verify the Fable mode install/activation chain end to end.

Run directly or via the `fable doctor` launcher subcommand. Exit code 1 only
on hard failures (missing core files, unparseable/unregistered settings,
live-fire failure); warnings and info lines never fail the run.

Env knobs:
  FABLE_DOCTOR_SKIP_CLI=1   skip the `claude --version` probe (offline/tests)
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")

FAILS = []
WARNS = []


def ok(msg):
    print("[ok] " + msg)


def fail(msg):
    FAILS.append(msg)
    print("[!!] " + msg)


def warn(msg):
    WARNS.append(msg)
    print("[--] " + msg)


def check_python():
    if sys.version_info >= (3, 9):
        ok("python {}.{}.{}".format(*sys.version_info[:3]))
    else:
        fail("python >= 3.9 required, running {}.{}".format(*sys.version_info[:2]))


CORE_FILES = [
    "FABLE_PLAYBOOK.md",
    "fable-code.md",
    "fable-system.md",
    os.path.join("hooks", "fable-trigger.py"),
    os.path.join("hooks", "test-after-edit.py"),
    os.path.join("skills", "fable", "SKILL.md"),
    os.path.join("agents", "grounding-verifier.md"),
]


def check_files():
    for rel in CORE_FILES:
        path = os.path.join(CLAUDE, rel)
        if os.path.isfile(path):
            ok("present: " + rel)
        else:
            fail("missing: " + path + "  (re-run install.py)")


def check_settings():
    path = os.path.join(CLAUDE, "settings.json")
    if not os.path.isfile(path):
        fail("settings.json missing (re-run install.py)")
        return
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        fail("settings.json unreadable: {}".format(e))
        return
    hooks = d.get("hooks", {})
    for event, needle in (("SessionStart", "fable-trigger.py"),
                          ("UserPromptSubmit", "fable-trigger.py"),
                          ("PostToolUse", "test-after-edit.py")):
        cmds = [h.get("command", "") for e in hooks.get(event, [])
                for h in e.get("hooks", [])]
        hit = next((c for c in cmds if needle in c), None)
        if not hit:
            fail("{} not registered for {} (re-run install.py)".format(needle, event))
            continue
        ok("{} registered for {}".format(needle, event))
        m = re.match(r'"([^"]+)"', hit)
        interp = m.group(1) if m else hit.split()[0]
        if not (os.path.isfile(interp) or shutil.which(interp)):
            fail("hook interpreter not found: " + interp)
    if d.get("alwaysThinkingEnabled") is not True:
        warn("alwaysThinkingEnabled is off - reasoning-density lever missing")


def check_claude_cli():
    if os.environ.get("FABLE_DOCTOR_SKIP_CLI") == "1":
        warn("claude CLI probe skipped (FABLE_DOCTOR_SKIP_CLI=1)")
        return
    if not shutil.which("claude"):
        warn("claude CLI not on PATH - the fable launcher won't start")
        return
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True,
                             text=True, timeout=30).stdout.strip()
    except Exception as e:
        warn("claude --version failed: {}".format(e))
        return
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
    if not m:
        warn("could not parse claude version from: " + out)
        return
    ver = tuple(int(x) for x in m.groups())
    label = ".".join(map(str, ver))
    if ver >= (2, 1, 199):
        ok("claude {} (effort exposed to hooks)".format(label))
    else:
        warn("claude {} < 2.1.199: effort not exposed to hooks; "
             "phrase/FABLE_MODE/SessionStart paths unaffected".format(label))


def _fire(payload, env_extra):
    hook = os.path.join(CLAUDE, "hooks", "fable-trigger.py")
    env = dict(os.environ)
    env.pop("CLAUDE_EFFORT", None)
    env.pop("FABLE_MODE", None)
    env.update(env_extra)
    p = subprocess.run([sys.executable, hook], input=json.dumps(payload),
                       capture_output=True, text=True, timeout=30, env=env)
    return p.stdout.strip()


def check_live_fire():
    if not os.path.isfile(os.path.join(CLAUDE, "hooks", "fable-trigger.py")):
        return  # already reported by check_files
    sid = "doctor-" + uuid.uuid4().hex[:8]
    try:
        ss = _fire({"hook_event_name": "SessionStart", "source": "startup",
                    "session_id": sid}, {"FABLE_MODE": "1"})
        ups = _fire({"prompt": "use fable", "session_id": sid + "-b"}, {})
    except Exception as e:
        fail("live fire errored: {}".format(e))
        return
    finally:
        for s in (sid, sid + "-b"):
            try:
                os.remove(os.path.join(tempfile.gettempdir(), "fable-loaded-" + s))
            except OSError:
                pass
    for name, out, event in (("SessionStart", ss, "SessionStart"),
                             ("UserPromptSubmit phrase", ups, "UserPromptSubmit")):
        try:
            payload = json.loads(out)["hookSpecificOutput"]
            assert payload["hookEventName"] == event
            assert "Fable mode active" in payload["additionalContext"]
            ok("live fire: {} injects".format(name))
        except Exception:
            fail("live fire: {} produced no/invalid injection: {!r}".format(
                name, out[:80]))


def check_evidence():
    files = glob.glob(os.path.join(CLAUDE, "projects", "*", "*.jsonl"))
    files.sort(key=os.path.getmtime, reverse=True)
    for path in files[:10]:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "Fable mode active" in line:
                        ok("injection seen in a recent session: "
                           + os.path.basename(path))
                        return
        except OSError:
            continue
    warn("no injection found in the 10 most recent transcripts "
         "(fine if you haven't used fable yet)")


def main():
    print("fable doctor - checking " + CLAUDE)
    check_python()
    check_files()
    check_settings()
    check_claude_cli()
    check_live_fire()
    check_evidence()
    print()
    if FAILS:
        print("RESULT: {} failure(s), {} warning(s) - Fable mode will not work "
              "correctly.".format(len(FAILS), len(WARNS)))
        sys.exit(1)
    print("RESULT: healthy ({} warning(s)).".format(len(WARNS)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run doctor tests**

Run: `python -m pytest tests/test_fable_doctor.py -v`
Expected: 3 tests PASS.

---

### Task 5: Install/uninstall wiring for the doctor

**Files:**
- Modify: `install.py` (hooks copy step)
- Modify: `uninstall.py` (hooks removal step)
- Test: `tests/test_install.py`, `tests/test_uninstall.py`

**Interfaces:**
- Consumes: `hooks/fable-doctor.py` (Task 4). Produces: `~/.claude/hooks/fable-doctor.py` present after install, absent after uninstall.

- [ ] **Step 1: Add failing assertions**

`tests/test_install.py`, in `test_install_copies_everything` after the `test-after-edit.py` assert:

```python
    assert (claude / "hooks" / "fable-doctor.py").is_file()
```

`tests/test_uninstall.py`, after the fable-trigger assert:

```python
    assert not (claude / "hooks" / "fable-doctor.py").exists()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_install.py tests/test_uninstall.py -v`
Expected: `test_install_copies_everything` FAILS; `test_uninstall_reverses_install` still PASSES (nothing installed → nothing left behind), which is acceptable — the install assert is the driving failure.

- [ ] **Step 3: Implement**

`install.py`, in the hooks step after `copy_into("hooks/test-after-edit.py", ...)`:

```python
    copy_into("hooks/fable-doctor.py", os.path.join(CLAUDE, "hooks"))
```

`uninstall.py`, in `main()` after the test-after-edit `rm_file`:

```python
    rm_file(os.path.join(CLAUDE, "hooks", "fable-doctor.py"))
```

- [ ] **Step 4: Run both test files**

Run: `python -m pytest tests/test_install.py tests/test_uninstall.py -v`
Expected: all PASS.

---

### Task 6: Playbook orchestration section + docs

**Files:**
- Modify: `FABLE_PLAYBOOK.md` (append section after Enforcement)
- Modify: `README.md` (bundle bullets)
- Modify: `CHANGELOG.md` (Unreleased → Added)

**Interfaces:**
- Consumes: `fable --ultra`, `fable doctor`, `FABLE_AUTO=0` from Tasks 1/3/4.

- [ ] **Step 1: Append to `FABLE_PLAYBOOK.md`** (after the Enforcement section's final bullet, at end of file)

```markdown

---

## Orchestration — scale the harness to the task

Fable's discipline is single-context by default; escalate deliberately:

- **Fan out when the task decomposes.** Independent units (N files to migrate,
  M subsystems to map, review dimensions) → parallel subagents, each with a
  scoped brief; synthesize in the main context. Never serialize what has no
  data dependency (Fix 3, applied to agents).
- **Verify adversarially.** Fan-in results are claims, not facts: route
  non-trivial ones through the evidence ledger, and spawn the cold
  `grounding-verifier` on the merged result — a subagent never self-approves
  its own output (Grounding section above).
- **Plan-gate before long autonomy.** Multi-phase runs get a phased plan and a
  live task list first; return to the plan at each phase boundary.
- **Calibrate ruthlessly.** One context that fits the whole task beats any
  orchestration. No multi-agent machinery for typo-class work.
- **Mechanical lever:** `fable --ultra` launches with `ultracode` — the harness
  auto-runs multi-agent workflows for substantive tasks. Heavy on tokens; the
  calibration rule above is the counterweight.
```

- [ ] **Step 2: Update `README.md` bundle bullets**

Replace the hooks bullet:

```markdown
- **Hooks** — `fable-trigger.py` injects the playbook at `xhigh`/`max`/`ultracode`; `test-after-edit.py` runs your project's tests after each edit and reports the result back — the one habit no model keeps on willpower.
```

with:

```markdown
- **Hooks** — `fable-trigger.py` injects the playbook when the launcher declares the mode, at `xhigh`/`max`/`ultracode` effort, on a trigger phrase, or **by itself when the prompt looks like a real task** (ru+en heuristic; opt out with `FABLE_AUTO=0`); `test-after-edit.py` runs your project's tests after each edit and reports the result back — the one habit no model keeps on willpower.
```

Replace the launcher bullet (from the previous rework) with:

```markdown
- **`fable` launcher** — pins `--model claude-opus-4-8`, appends `fable-code.md`, sets `xhigh` effort, and declares the mode via `FABLE_MODE=1` so the playbook injects at session start on every Claude Code version (`fable.zsh` for Unix shells, `fable.ps1` for PowerShell). `fable --ultra` adds ultracode multi-agent orchestration; `fable doctor` verifies the whole install/activation chain in one command.
```

- [ ] **Step 3: Update `CHANGELOG.md`** — under `## [Unreleased]` → `### Added`, prepend:

```markdown
- Auto-activation: `fable-trigger.py` scores prompt complexity (ru+en signals:
  task verbs, code fences, file paths, multi-step markers, length) and loads
  the playbook by itself for task-shaped prompts, once per session, in any
  session — no launcher or phrase needed. Opt out with `FABLE_AUTO=0`.
- `fable --ultra` (alias `-u`): launches with ultracode auto-orchestration; new
  "Orchestration" section in the playbook (fan-out, adversarial verification
  via `grounding-verifier`, plan-gating, calibration).
- `fable doctor`: one-command diagnosis of the install/activation chain —
  files, registered hooks, interpreter paths, Claude Code version, a live-fire
  injection test, and transcript evidence of past activations.
- The `/fable` skill triggers proactively at the start of non-trivial tasks.
```

- [ ] **Step 4: Full suite**

Run: `python -m pytest -q`
Expected: all tests PASS (29 + 3 doctor = 32 or more, exact count printed).

---

## Self-Review Notes

- Spec coverage: §1 → Tasks 1–2, §2 → Tasks 3 + 6, §3 → Tasks 3–5, §4 → Tasks 5–6. No gaps.
- Consistency: `FABLE_AUTO`, `FABLE_DOCTOR_SKIP_CLI`, `fable-doctor.py`, reason string `auto`,
  `--ultra`/`-u` used identically across tasks.
- The doctor's `check_evidence` scans only the 10 newest transcripts by mtime — bounded I/O.
