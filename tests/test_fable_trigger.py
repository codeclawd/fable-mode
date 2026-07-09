"""Tests for hooks/fable-trigger.py — the dual-event Fable injector."""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / "hooks" / "fable-trigger.py"

CODE_BODY = (
    "# FABLE_CODE_MARKER_7\n\nrules here\n\n---\n\n"
    "## Relationship to the rest of the bundle\n\nHUMAN_ONLY_TAIL\n"
)


def run(stdin_obj, home, tmpdir, env_extra=None):
    env = dict(os.environ)
    env["HOME"] = str(home)          # expanduser on POSIX
    env["USERPROFILE"] = str(home)   # expanduser on Windows
    env["TMPDIR"] = str(tmpdir)      # isolate session markers per test
    env["TEMP"] = str(tmpdir)
    env["TMP"] = str(tmpdir)
    env.pop("CLAUDE_EFFORT", None)
    env.pop("FABLE_DISABLE", None)
    env.pop("FABLE_MODE", None)
    env.pop("FABLE_CODE_APPENDED", None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, str(HOOK)],
                       input=json.dumps(stdin_obj), text=True,
                       capture_output=True, env=env)
    return p.stdout.strip()


def make_home(tmp_path, with_playbook=True, with_code=True, with_harness=False):
    claude = tmp_path / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    if with_playbook:
        (claude / "FABLE_PLAYBOOK.md").write_text("PLAYBOOK_MARKER_42", encoding="utf-8")
    if with_code:
        (claude / "FABLE_CODE.md").write_text(CODE_BODY, encoding="utf-8")
    if with_harness:
        (claude / "docs").mkdir(exist_ok=True)
        (claude / "docs" / "LOOP-HARNESS.md").write_text("harness", encoding="utf-8")
    return tmp_path


def ctx_of(out):
    return json.loads(out)["hookSpecificOutput"]["additionalContext"]


# ── Layer 1: FABLE_CODE.md rules ────────────────────────────────────────────

def test_first_prompt_injects_code_layer(tmp_path):
    home = make_home(tmp_path)
    out = run({"prompt": "hello world", "session_id": str(uuid.uuid4())}, home, tmp_path)
    assert out, "first prompt should inject the FABLE_CODE layer"
    ctx = ctx_of(out)
    assert "FABLE_CODE_MARKER_7" in ctx
    assert "HUMAN_ONLY_TAIL" not in ctx, "human-readers tail must be stripped"


def test_code_layer_once_per_session(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    assert run({"prompt": "hi", "session_id": sid}, home, tmp_path)
    assert run({"prompt": "hi again", "session_id": sid}, home, tmp_path) == ""


def test_code_appended_skips_layer1(tmp_path):
    """When the launcher already appended FABLE_CODE.md, don't re-inject."""
    home = make_home(tmp_path)
    out = run({"prompt": "hi", "session_id": str(uuid.uuid4())}, home, tmp_path,
              env_extra={"FABLE_CODE_APPENDED": "1"})
    # Layer 1 skipped, but a trivial prompt doesn't trigger the playbook either
    assert out == "" or "FABLE_PLAYBOOK.md" not in ctx_of(out)


# ── Layer 2: Playbook directive (never inlined) ─────────────────────────────

def test_phrase_injects_playbook_directive_not_body(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    run({"prompt": "hi", "session_id": sid}, home, tmp_path)  # consume layer 1
    out = run({"prompt": "please use fable here", "session_id": sid}, home, tmp_path)
    assert out, "phrase should trigger even after layer 1 fired"
    ctx = ctx_of(out)
    assert "FABLE_PLAYBOOK.md" in ctx, "directive must name the playbook path"
    assert "PLAYBOOK_MARKER_42" not in ctx, "playbook body must NOT be inlined (10k cap)"


def test_effort_directive_once_per_session(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    first = run({"prompt": "hi", "effort": {"level": "xhigh"}, "session_id": sid}, home, tmp_path)
    assert "FABLE_PLAYBOOK.md" in ctx_of(first)
    second = run({"prompt": "hi", "effort": {"level": "xhigh"}, "session_id": sid}, home, tmp_path)
    assert second == "", "effort path debounces after the first prompt"


def test_effort_accepts_plain_string(tmp_path):
    home = make_home(tmp_path)
    out = run({"prompt": "hi", "effort": "ultracode",
               "session_id": str(uuid.uuid4())}, home, tmp_path)
    assert "FABLE_PLAYBOOK.md" in ctx_of(out)


def test_user_prompt_field_name_also_works(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    run({"prompt": "hi", "session_id": sid}, home, tmp_path)
    out = run({"user_prompt": "use fable", "session_id": sid}, home, tmp_path)
    assert out and "FABLE_PLAYBOOK.md" in ctx_of(out)


# ── Auto-activation heuristic ───────────────────────────────────────────────

def test_auto_heuristic_triggers_on_complex_prompt(tmp_path):
    """A task-shaped prompt auto-loads the playbook without a phrase."""
    home = make_home(tmp_path)
    prompt = (
        "Implement a function that reads the config file at src/config.ts "
        "and refactors the parsing logic.\n\n"
        "```\nold_code_here\n```\n\n"
        "Steps:\n1. Read the file\n2. Extract the parser\n3. Write tests"
    )
    out = run({"prompt": prompt, "session_id": str(uuid.uuid4())}, home, tmp_path)
    assert "FABLE_PLAYBOOK.md" in ctx_of(out)


def test_auto_heuristic_opt_out(tmp_path):
    home = make_home(tmp_path)
    prompt = "Implement a function that reads src/config.ts and refactors it."
    out = run({"prompt": prompt, "session_id": str(uuid.uuid4())}, home, tmp_path,
              env_extra={"FABLE_AUTO": "0"})
    ctx = ctx_of(out)
    assert "FABLE_PLAYBOOK.md" not in ctx, "FABLE_AUTO=0 disables auto-activation"


def test_simple_prompt_does_not_auto_trigger(tmp_path):
    home = make_home(tmp_path)
    out = run({"prompt": "what is 2+2", "session_id": str(uuid.uuid4())}, home, tmp_path)
    ctx = ctx_of(out)
    assert "FABLE_PLAYBOOK.md" not in ctx


# ── FABLE_MODE (launcher-declared) ──────────────────────────────────────────

def test_fable_mode_triggers_playbook(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    out = run({"prompt": "hi", "session_id": sid}, home, tmp_path,
              env_extra={"FABLE_MODE": "1"})
    assert "FABLE_PLAYBOOK.md" in ctx_of(out)
    # Once per session
    second = run({"prompt": "hi", "session_id": sid}, home, tmp_path,
                 env_extra={"FABLE_MODE": "1"})
    assert "FABLE_PLAYBOOK.md" not in second


# ── SessionStart event ──────────────────────────────────────────────────────

def test_session_start_with_fable_mode(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    out = run({"hook_event_name": "SessionStart", "source": "startup",
               "session_id": sid}, home, tmp_path,
              env_extra={"FABLE_MODE": "1"})
    ctx = ctx_of(out)
    assert "FABLE_CODE_MARKER_7" in ctx, "SessionStart injects code rules"
    assert "FABLE_PLAYBOOK.md" in ctx, "SessionStart injects playbook directive"


def test_session_start_resume_no_double_inject(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    run({"hook_event_name": "SessionStart", "source": "startup",
         "session_id": sid}, home, tmp_path, env_extra={"FABLE_MODE": "1"})
    out = run({"hook_event_name": "SessionStart", "source": "resume",
               "session_id": sid}, home, tmp_path, env_extra={"FABLE_MODE": "1"})
    assert out == "", "resume should not double-inject"


def test_session_start_compact_restores(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    # First, activate via a prompt to stamp the markers
    run({"prompt": "hi", "effort": {"level": "xhigh"}, "session_id": sid},
        home, tmp_path)
    # Compaction wipes context; SessionStart should restore
    out = run({"hook_event_name": "SessionStart", "source": "compact",
               "session_id": sid}, home, tmp_path)
    ctx = ctx_of(out)
    assert "FABLE_PLAYBOOK.md" in ctx, "compact restores the playbook directive"


def test_session_start_clear_re_arms(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    run({"prompt": "use fable", "session_id": sid}, home, tmp_path)
    # Clear should drop the marker
    run({"hook_event_name": "SessionStart", "source": "clear",
         "session_id": sid}, home, tmp_path)
    # Now a new prompt should re-inject
    out = run({"prompt": "use fable", "session_id": sid}, home, tmp_path)
    assert "FABLE_PLAYBOOK.md" in ctx_of(out)


def test_session_start_without_fable_mode_silent(tmp_path):
    home = make_home(tmp_path)
    out = run({"hook_event_name": "SessionStart", "source": "startup",
               "session_id": str(uuid.uuid4())}, home, tmp_path)
    assert out == "", "SessionStart without FABLE_MODE on a fresh session is silent"


# ── Harness bridge ──────────────────────────────────────────────────────────

def test_harness_bridge_line(tmp_path):
    home = make_home(tmp_path, with_harness=True)
    out = run({"prompt": "hi", "session_id": str(uuid.uuid4())}, home, tmp_path)
    assert "LOOP-HARNESS.md" in ctx_of(out)


def test_no_harness_no_bridge(tmp_path):
    home = make_home(tmp_path, with_harness=False)
    out = run({"prompt": "hi", "session_id": str(uuid.uuid4())}, home, tmp_path)
    assert "LOOP-HARNESS.md" not in ctx_of(out)


# ── Cap safety ──────────────────────────────────────────────────────────────

def test_context_stays_under_cap_with_real_files(tmp_path):
    """The shipped FABLE_CODE.md (not a stub) must inject under the 10k cap."""
    home = tmp_path
    claude = home / ".claude"
    (claude / "docs").mkdir(parents=True)
    (claude / "FABLE_CODE.md").write_text(
        (REPO / "FABLE_CODE.md").read_text(encoding="utf-8"), encoding="utf-8")
    (claude / "FABLE_PLAYBOOK.md").write_text("x", encoding="utf-8")
    (claude / "docs" / "LOOP-HARNESS.md").write_text("harness", encoding="utf-8")
    out = run({"prompt": "use fable", "session_id": str(uuid.uuid4())}, home, tmp_path)
    ctx = ctx_of(out)
    assert len(ctx) <= 10000
    assert "[truncated" not in ctx, "real files must fit without truncation"


# ── Safety ──────────────────────────────────────────────────────────────────

def test_missing_everything_is_silent(tmp_path):
    home = make_home(tmp_path, with_playbook=False, with_code=False)
    assert run({"prompt": "use fable", "session_id": str(uuid.uuid4())}, home, tmp_path) == ""


def test_disable_env_var(tmp_path):
    home = make_home(tmp_path)
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["FABLE_DISABLE"] = "1"
    p = subprocess.run([sys.executable, str(HOOK)],
                       input=json.dumps({"prompt": "use fable", "session_id": "s"}),
                       text=True, capture_output=True, env=env)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_malformed_input_never_crashes(tmp_path):
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["USERPROFILE"] = str(tmp_path)
    p = subprocess.run([sys.executable, str(HOOK)], input="not json",
                       text=True, capture_output=True, env=env)
    assert p.returncode == 0
    assert p.stdout.strip() == ""
