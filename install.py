#!/usr/bin/env python3
"""One-command, cross-platform installer for Fable mode (Windows / macOS / Linux).

    python  install.py     # Windows
    python3 install.py     # macOS / Linux

Python is already a hard dependency (the hooks are Python), so the installer is
Python too: one source of truth, identical behavior on every OS. install.sh and
install.ps1 are thin native wrappers that just locate Python and exec this file.

Idempotent. Backs up an existing settings.json. The interpreter written into the
hook commands is sys.executable — the exact, absolute Python that ran this script.
"""
import os
import sys
import shutil
import subprocess

REPO = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
IS_WINDOWS = os.name == "nt"

sys.path.insert(0, os.path.join(REPO, "scripts"))
from merge_settings import merge  # noqa: E402


def copy_into(rel_file, dst_dir):
    shutil.copy(os.path.join(REPO, rel_file), os.path.join(dst_dir, os.path.basename(rel_file)))


def copytree_idempotent(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def append_once(path, marker, block):
    """Append `block` to `path` unless `marker` already appears in it."""
    existing = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = f.read()
    if marker in existing:
        print("  launcher already present in {} - skipped".format(path))
        return
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(block)
    print("  added launcher to {}".format(path))


def powershell_profile_path():
    """Ask the available PowerShell for its $PROFILE; fall back to the PS7 default."""
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


def install_launcher():
    if IS_WINDOWS:
        profile = powershell_profile_path()
        src = os.path.join(REPO, "shell", "fable.ps1")
        block = ('\n# Fable mode (added by fable-mode/install.py)\n. "{}"\n'.format(src))
        append_once(profile, "fable.ps1", block)
    else:
        shell = os.environ.get("SHELL", "")
        rc = os.path.join(HOME, ".bashrc" if "bash" in shell else ".zshrc")
        src = os.path.join(REPO, "shell", "fable.zsh")
        block = ('\n# Fable mode (added by fable-mode/install.py)\nsource "{}"\n'.format(src))
        append_once(rc, "fable.zsh", block)


def main():
    for sub in ("hooks", "skills", "agents"):
        os.makedirs(os.path.join(CLAUDE, sub), exist_ok=True)

    if not shutil.which("claude"):
        print("warning: 'claude' CLI not found on PATH - install Claude Code before running 'fable'.")

    print("-> hooks")
    copy_into("hooks/fable-trigger.py", os.path.join(CLAUDE, "hooks"))
    copy_into("hooks/test-after-edit.py", os.path.join(CLAUDE, "hooks"))

    print("-> playbook")
    copy_into("FABLE_PLAYBOOK.md", CLAUDE)

    print("-> fable system prompt")
    copy_into("fable-system.md", CLAUDE)

    print("-> fable behavior layer (Claude Code)")
    copy_into("fable-code.md", CLAUDE)

    print("-> skills (all bundled) + agent")
    skills_dir = os.path.join(REPO, "skills")
    for name in sorted(os.listdir(skills_dir)):
        src = os.path.join(skills_dir, name)
        if os.path.isdir(src):
            copytree_idempotent(src, os.path.join(CLAUDE, "skills", name))
    copy_into("agents/grounding-verifier.md", os.path.join(CLAUDE, "agents"))

    print("-> launcher")
    install_launcher()

    print("-> settings.json (alwaysThinkingEnabled + hooks; backup written)")
    merge(os.path.join(CLAUDE, "settings.json"), sys.executable, os.path.join(CLAUDE, "hooks"))

    print()
    print("Done. Now:")
    if IS_WINDOWS:
        print("  1. . $PROFILE      (reload your PowerShell profile)")
    else:
        print("  1. source your shell rc (e.g. source ~/.zshrc)")
    print("  2. run: fable")


if __name__ == "__main__":
    main()
