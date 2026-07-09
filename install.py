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

BUNDLED_MARKER = ".fable-mode-bundled"


def copy_into(rel_file, dst_dir):
    shutil.copy(os.path.join(REPO, rel_file), os.path.join(dst_dir, os.path.basename(rel_file)))


def install_skill(src, dst):
    """Copy one bundled skill into ~/.claude/skills. A pre-existing directory
    without our marker file was NOT installed by fable-mode — it's the user's
    own work, so move it to ~/.claude/backups/skills/<name> instead of
    deleting it. Re-runs (marker present) just refresh our copy."""
    marker = os.path.join(dst, BUNDLED_MARKER)
    if os.path.isdir(dst) and not os.path.isfile(marker):
        bak = os.path.join(CLAUDE, "backups", "skills", os.path.basename(dst))
        if os.path.exists(bak):
            shutil.rmtree(dst)  # the user's copy is already preserved there
        else:
            os.makedirs(os.path.dirname(bak), exist_ok=True)
            shutil.move(dst, bak)
            print("  existing skill not installed by fable-mode - saved to {}".format(bak))
    elif os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    open(marker, "w").close()


def ensure_launcher(path, marker, block):
    """Make `block` the launcher entry in `path`. A line referencing `marker`
    that points elsewhere (an old clone path) is replaced — append-once
    semantics would silently keep the stale, broken line."""
    existing = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = f.read()
    if block.strip("\n") in existing:
        print("  launcher already present in {} - skipped".format(path))
        return
    out, replaced = [], False
    for line in existing.splitlines(keepends=True):
        if marker in line:
            replaced = True
            while out and (out[-1].lstrip().startswith("# Fable mode")
                           or out[-1].strip() == ""):
                out.pop()
            continue
        out.append(line)
    existing = "".join(out)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            existing += "\n"
        f.write(existing + block)
    print("  {} launcher in {}".format("updated stale" if replaced else "added", path))


def powershell_profile_paths():
    """$PROFILE of every PowerShell present (pwsh 7 and Windows PowerShell 5.1).
    A user may open either shell, so the launcher goes into each."""
    paths = []
    for exe in ("pwsh", "powershell"):
        if shutil.which(exe):
            try:
                out = subprocess.run([exe, "-NoProfile", "-Command", "$PROFILE"],
                                     capture_output=True, text=True, timeout=20)
                p = out.stdout.strip()
                if p and p not in paths:
                    paths.append(p)
            except Exception:
                pass
    if not paths:
        paths.append(os.path.join(HOME, "Documents", "PowerShell",
                                  "Microsoft.PowerShell_profile.ps1"))
    return paths


def install_launcher():
    """Copy the launchers into ~/.claude/shell and source them from there.
    Sourcing the stable copy (not the clone) keeps every profile working if
    the checkout is later moved or deleted."""
    shell_dir = os.path.join(CLAUDE, "shell")
    os.makedirs(shell_dir, exist_ok=True)
    copy_into("shell/fable.ps1", shell_dir)
    copy_into("shell/fable.zsh", shell_dir)
    if IS_WINDOWS:
        block = ('\n# Fable mode (added by fable-mode/install.py)\n. "{}"\n'
                 .format(os.path.join(shell_dir, "fable.ps1")))
        for profile in powershell_profile_paths():
            ensure_launcher(profile, "fable.ps1", block)
    else:
        shell = os.environ.get("SHELL", "")
        rc = os.path.join(HOME, ".bashrc" if "bash" in shell else ".zshrc")
        block = ('\n# Fable mode (added by fable-mode/install.py)\nsource "{}"\n'
                 .format(os.path.join(shell_dir, "fable.zsh")))
        ensure_launcher(rc, "fable.zsh", block)


def main():
    for sub in ("hooks", "skills", "agents"):
        os.makedirs(os.path.join(CLAUDE, sub), exist_ok=True)

    if not shutil.which("claude"):
        print("warning: 'claude' CLI not found on PATH - install Claude Code before running 'fable'.")

    print("-> hooks")
    copy_into("hooks/fable-trigger.py", os.path.join(CLAUDE, "hooks"))
    copy_into("hooks/test-after-edit.py", os.path.join(CLAUDE, "hooks"))
    copy_into("hooks/fable-doctor.py", os.path.join(CLAUDE, "hooks"))

    print("-> playbook + native distillation")
    copy_into("FABLE_PLAYBOOK.md", CLAUDE)
    copy_into("FABLE_CODE.md", CLAUDE)

    print("-> ultracode settings")
    shell_dir = os.path.join(CLAUDE, "shell")
    os.makedirs(shell_dir, exist_ok=True)
    copy_into("shell/ultracode.settings.json", shell_dir)

    print("-> skills (all bundled) + agent")
    skills_dir = os.path.join(REPO, "skills")
    for name in sorted(os.listdir(skills_dir)):
        src = os.path.join(skills_dir, name)
        if os.path.isdir(src):
            install_skill(src, os.path.join(CLAUDE, "skills", name))
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
    print("  3. verify: fable doctor")


if __name__ == "__main__":
    main()
