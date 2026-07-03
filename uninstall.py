#!/usr/bin/env python3
"""Cross-platform uninstaller for Fable mode (Windows / macOS / Linux).

    python  uninstall.py     # Windows
    python3 uninstall.py     # macOS / Linux

Reverses install.py: removes the files it copied into ~/.claude, strips the
launcher line from your shell rc / PowerShell $PROFILE, and removes the two hook
entries it added to settings.json (writing a fresh backup first).

Conservative on purpose:
  - Only removes the skill directories this repo bundles, never your other skills.
  - Leaves ~/.claude itself and "alwaysThinkingEnabled" untouched (toggle that in
    /config if you want it off — it may predate the install).
"""
import os
import sys
import json
import shutil

REPO = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
IS_WINDOWS = os.name == "nt"


def rm_file(path):
    if os.path.isfile(path):
        os.remove(path)
        print("  removed " + path)


def rm_tree(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
        print("  removed " + path)


def bundled_skill_names():
    skills_dir = os.path.join(REPO, "skills")
    if not os.path.isdir(skills_dir):
        return []
    return [n for n in os.listdir(skills_dir)
            if os.path.isdir(os.path.join(skills_dir, n))]


def strip_launcher(path, marker):
    """Remove the '# Fable mode' comment + the source/dot line referencing `marker`."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    out, removed = [], False
    for line in lines:
        if marker in line:
            removed = True
            # drop a preceding "# Fable mode" comment and a blank line if present
            while out and (out[-1].lstrip().startswith("# Fable mode")
                           or out[-1].strip() == ""):
                out.pop()
            continue
        out.append(line)
    if removed:
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(out))
        print("  removed launcher from " + path)


def powershell_profile_path():
    import subprocess
    for exe in ("pwsh", "powershell"):
        if shutil.which(exe):
            try:
                out = subprocess.run([exe, "-NoProfile", "-Command", "$PROFILE"],
                                     capture_output=True, text=True, timeout=20)
                p = out.stdout.strip()
                if p:
                    return p
            except Exception:
                pass
    return os.path.join(HOME, "Documents", "PowerShell",
                        "Microsoft.PowerShell_profile.ps1")


def remove_launcher():
    if IS_WINDOWS:
        strip_launcher(powershell_profile_path(), "fable.ps1")
    else:
        for rc in (".zshrc", ".bashrc"):
            strip_launcher(os.path.join(HOME, rc), "fable.zsh")


def clean_settings():
    path = os.path.join(CLAUDE, "settings.json")
    if not os.path.isfile(path):
        return
    try:
        with open(path) as f:
            d = json.load(f)
    except Exception:
        print("  settings.json unreadable — left untouched")
        return
    shutil.copy(path, path + ".uninstall.bak")

    hooks = d.get("hooks", {})
    for event in ("SessionStart", "UserPromptSubmit", "PostToolUse"):
        arr = hooks.get(event)
        if not isinstance(arr, list):
            continue
        kept = []
        for entry in arr:
            cmds = " ".join(h.get("command", "")
                            for h in entry.get("hooks", []))
            if "fable-trigger.py" in cmds or "test-after-edit.py" in cmds:
                continue  # drop the entry we added
            kept.append(entry)
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    if not hooks:
        d.pop("hooks", None)
    elif "hooks" in d:
        d["hooks"] = hooks

    with open(path, "w") as f:
        json.dump(d, f, indent=2)
    print("  removed Fable hooks from settings.json (backup: settings.json.uninstall.bak)")


def main():
    print("-> files in ~/.claude")
    rm_file(os.path.join(CLAUDE, "hooks", "fable-trigger.py"))
    rm_file(os.path.join(CLAUDE, "hooks", "test-after-edit.py"))
    rm_file(os.path.join(CLAUDE, "FABLE_PLAYBOOK.md"))
    rm_file(os.path.join(CLAUDE, "fable-system.md"))
    rm_file(os.path.join(CLAUDE, "fable-code.md"))
    rm_file(os.path.join(CLAUDE, "agents", "grounding-verifier.md"))
    for name in bundled_skill_names():
        rm_tree(os.path.join(CLAUDE, "skills", name))

    print("-> launcher")
    remove_launcher()

    print("-> settings.json")
    clean_settings()

    print()
    print("Done. Fable mode removed. ~/.claude and 'alwaysThinkingEnabled' were kept.")
    print("Reload your shell ('. $PROFILE' or 'source ~/.zshrc') to drop the 'fable' command.")


if __name__ == "__main__":
    main()
