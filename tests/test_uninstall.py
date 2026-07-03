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
    mod.powershell_profile_paths = lambda: [str(tmp_path / "profile.ps1")]
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
    assert not (claude / "ultracode.settings.json").exists()
    assert not (claude / "hooks" / "fable-trigger.py").exists()
    assert not (claude / "hooks" / "fable-doctor.py").exists()
    assert not (claude / "skills" / "fable").exists()
    assert not (claude / "skills" / "ground").exists()
    assert not (claude / "shell" / "fable.ps1").exists()
    assert not (claude / "shell" / "fable.zsh").exists()
    assert "fable.ps1" not in (tmp_path / "profile.ps1").read_text(encoding="utf-8")

    s = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    ss = s["hooks"]["SessionStart"]
    assert len(ss) == 1 and "keepme.cjs" in ss[0]["hooks"][0]["command"]
    assert "UserPromptSubmit" not in s["hooks"]
    assert "PostToolUse" not in s["hooks"]
    assert s["alwaysThinkingEnabled"] is True


def test_uninstall_leaves_skills_it_did_not_install(tmp_path):
    """Skill removal is gated on the .fable-mode-bundled marker: a same-named
    directory the user owns (no marker) must survive the uninstall."""
    inst = sandbox(load("fable_install", "install.py"), tmp_path)
    uninst = sandbox(load("fable_uninstall", "uninstall.py"), tmp_path)
    inst.main()

    claude = tmp_path / ".claude"
    (claude / "skills" / "ground" / ".fable-mode-bundled").unlink()  # now "user-owned"
    foreign = claude / "skills" / "my-own-skill"
    foreign.mkdir(parents=True)
    (foreign / "SKILL.md").write_text("mine", encoding="utf-8")

    uninst.main()

    assert (claude / "skills" / "ground" / "SKILL.md").is_file()
    assert (foreign / "SKILL.md").is_file()
    assert not (claude / "skills" / "fable").exists()
