"""Tests for hooks/fable-trigger.py — the on-demand playbook injector."""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / "hooks" / "fable-trigger.py"


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


def make_home(tmp_path, with_playbook=True):
    claude = tmp_path / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    if with_playbook:
        (claude / "FABLE_PLAYBOOK.md").write_text("PLAYBOOK_MARKER_42", encoding="utf-8")
    return tmp_path


def test_phrase_injects_playbook(tmp_path):
    home = make_home(tmp_path)
    out = run({"prompt": "please use fable here", "session_id": str(uuid.uuid4())}, home)
    assert out, "phrase trigger should produce output"
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "PLAYBOOK_MARKER_42" in ctx


def test_no_phrase_low_effort_is_silent(tmp_path):
    home = make_home(tmp_path)
    assert run({"prompt": "hello world", "session_id": str(uuid.uuid4())}, home) == ""


def test_effort_injects_once_per_session(tmp_path):
    home = make_home(tmp_path)
    sid = str(uuid.uuid4())
    first = run({"prompt": "hi", "effort": "ultracode", "session_id": sid}, home)
    second = run({"prompt": "hi", "effort": "ultracode", "session_id": sid}, home)
    assert first, "first effort-only trigger should inject"
    assert second == "", "same session should be debounced on the second prompt"


def test_missing_playbook_is_silent(tmp_path):
    home = make_home(tmp_path, with_playbook=False)
    assert run({"prompt": "use fable", "session_id": str(uuid.uuid4())}, home) == ""


def test_malformed_input_never_crashes(tmp_path):
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["USERPROFILE"] = str(tmp_path)
    p = subprocess.run([sys.executable, str(HOOK)], input="not json",
                       text=True, capture_output=True, env=env)
    assert p.returncode == 0
    assert p.stdout.strip() == ""


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

