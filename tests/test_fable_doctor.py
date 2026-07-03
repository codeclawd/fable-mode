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
