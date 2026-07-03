"""Tests for install.py — the cross-platform installer.

Loads install.py as a module and redirects HOME / CLAUDE / the PowerShell profile
into a temp sandbox, so the real ~/.claude is never touched. Both launcher
branches (PowerShell + Unix shell rc) are exercised regardless of the host OS.
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_install():
    spec = importlib.util.spec_from_file_location("fable_install", REPO / "install.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sandbox(tmp_path, windows):
    inst = load_install()
    inst.HOME = str(tmp_path)
    inst.CLAUDE = str(tmp_path / ".claude")
    inst.IS_WINDOWS = windows
    inst._profile = tmp_path / "profile.ps1"
    inst.powershell_profile_path = lambda: str(inst._profile)
    return inst


def test_install_copies_everything(tmp_path):
    inst = sandbox(tmp_path, windows=True)
    inst.main()
    claude = tmp_path / ".claude"

    assert (claude / "FABLE_PLAYBOOK.md").is_file()
    assert (claude / "fable-system.md").is_file()
    assert (claude / "fable-code.md").is_file()
    assert (claude / "ultracode.settings.json").is_file()
    assert (claude / "skills" / "fable" / "SKILL.md").is_file()
    assert (claude / "hooks" / "fable-trigger.py").is_file()
    assert (claude / "hooks" / "test-after-edit.py").is_file()
    assert (claude / "hooks" / "fable-doctor.py").is_file()
    assert (claude / "agents" / "grounding-verifier.md").is_file()
    assert (claude / "skills" / "ground" / "SKILL.md").is_file()
    # nested skill content must survive the copy
    assert (claude / "skills" / "mcp-builder" / "reference" / "evaluation.md").is_file()
    # launcher written to the (sandboxed) PowerShell profile
    assert "fable.ps1" in (tmp_path / "profile.ps1").read_text(encoding="utf-8")

    s = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    assert s["alwaysThinkingEnabled"] is True
    cmd = s["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    assert sys.executable in cmd  # absolute interpreter, not a bare "python3"
    ss_cmd = s["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "fable-trigger.py" in ss_cmd


def test_install_is_idempotent(tmp_path):
    inst = sandbox(tmp_path, windows=True)
    inst.main()
    inst.main()
    claude = tmp_path / ".claude"

    s = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    assert len(s["hooks"]["UserPromptSubmit"]) == 1
    assert len(s["hooks"]["PostToolUse"]) == 1
    assert len(s["hooks"]["SessionStart"]) == 1
    assert (tmp_path / "profile.ps1").read_text(encoding="utf-8").count("fable.ps1") == 1
    assert (claude / "settings.json.bak").is_file()


def test_install_unix_launcher(tmp_path, monkeypatch):
    inst = sandbox(tmp_path, windows=False)
    monkeypatch.setenv("SHELL", "/bin/zsh")
    inst.main()
    rc = tmp_path / ".zshrc"
    assert rc.is_file()
    assert "fable.zsh" in rc.read_text(encoding="utf-8")
