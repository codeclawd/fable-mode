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
    (claude / "shell").mkdir(parents=True)
    for rel in ("FABLE_PLAYBOOK.md", "fable-code.md", "fable-system.md",
                "ultracode.settings.json"):
        (claude / rel).write_text("PLAYBOOK", encoding="utf-8")
    (claude / "shell" / "fable.ps1").write_text("# stub", encoding="utf-8")
    (claude / "shell" / "fable.zsh").write_text("# stub", encoding="utf-8")
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


def test_stale_launcher_path_is_a_hard_failure(tmp_path):
    """A profile line sourcing a fable launcher that no longer exists breaks
    every new shell - doctor must catch exactly this."""
    fake_install(tmp_path)
    (tmp_path / ".zshrc").write_text(
        '# Fable mode (added by fable-mode/install.py)\n'
        'source "/nonexistent/shell/fable.zsh"\n', encoding="utf-8")
    p = run_doctor(tmp_path)
    assert p.returncode == 1
    assert "launcher" in p.stdout.lower() and "missing" in p.stdout.lower()


def test_healthy_launcher_line_is_ok(tmp_path):
    fake_install(tmp_path)
    target = tmp_path / ".claude" / "shell" / "fable.zsh"
    (tmp_path / ".zshrc").write_text(
        'source "{}"\n'.format(str(target).replace("\\", "\\\\")), encoding="utf-8")
    p = run_doctor(tmp_path)
    assert p.returncode == 0, p.stdout


def fake_claude_bin(tmp_path):
    """A fake `claude` that answers --version and prints its flags the way the
    real CLI does: the file variant only as the `[-file]` bracket shorthand."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    if os.name == "nt":
        (bindir / "claude.cmd").write_text(
            '@echo off\r\n'
            'if "%1"=="--version" echo 2.1.199 (Claude Code)\r\n'
            'if "%1"=="--help" echo   --effort ^<level^>\r\n'
            'if "%1"=="--help" echo   via: --append-system-prompt[-file]\r\n',
            encoding="ascii")
    else:
        f = bindir / "claude"
        f.write_text('#!/bin/sh\n'
                     'case "$1" in\n'
                     '  --version) echo "2.1.199 (Claude Code)";;\n'
                     '  --help) echo "  --effort <level>";'
                     ' echo "  via: --append-system-prompt[-file]";;\n'
                     'esac\n', encoding="ascii")
        f.chmod(0o755)
    return str(bindir)


def test_bracket_shorthand_in_help_is_not_a_missing_flag(tmp_path):
    """The real CLI lists --append-system-prompt-file only as the
    `--append-system-prompt[-file]` shorthand; the probe must not warn."""
    fake_install(tmp_path)
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["USERPROFILE"] = str(tmp_path)
    env["PATH"] = fake_claude_bin(tmp_path) + os.pathsep + env.get("PATH", "")
    env.pop("FABLE_DOCTOR_SKIP_CLI", None)
    env.pop("CLAUDE_EFFORT", None)
    env.pop("FABLE_MODE", None)
    p = subprocess.run([sys.executable, str(DOCTOR)], capture_output=True,
                       text=True, env=env)
    assert "claude 2.1.199" in p.stdout, p.stdout
    assert "--append-system-prompt-file" not in p.stdout, (
        "bracket shorthand in --help was misread as a missing flag")
    assert p.returncode == 0, p.stdout


def test_hooks_in_settings_local_json_count_as_registered(tmp_path):
    fake_install(tmp_path)
    claude = tmp_path / ".claude"
    s = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    hooks = s.pop("hooks")
    (claude / "settings.json").write_text(json.dumps(s), encoding="utf-8")
    (claude / "settings.local.json").write_text(json.dumps({"hooks": hooks}),
                                                encoding="utf-8")
    p = run_doctor(tmp_path)
    assert "not registered" not in p.stdout
    assert p.returncode == 0, p.stdout
