#!/usr/bin/env python3
"""Merge Fable-mode settings into an existing Claude Code settings.json.

Importable (`from merge_settings import merge`) and runnable as a script. Writes
ABSOLUTE paths for both the Python interpreter and the hook scripts, so the
resulting hook commands work the same on macOS, Linux, and Windows — no reliance
on `$HOME` expansion or a `python3` alias being present at hook-run time.

Usage (script):
    merge_settings.py <settings.json> <python-exe> <hooks-dir>
"""
import json
import os
import sys
import shutil


def merge(settings_path, py, hooks_dir):
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            d = json.load(f)
        # Preserve the pristine pre-install settings exactly once. A naive
        # copy-every-run would, on the second install, overwrite this backup with
        # already-merged content — destroying the only good restore point.
        backup = settings_path + ".bak"
        if not os.path.exists(backup):
            shutil.copy(settings_path, backup)
    else:
        d = {}

    d["alwaysThinkingEnabled"] = True
    hooks = d.setdefault("hooks", {})

    def cmd(name):
        return '"{}" "{}"'.format(py, os.path.join(hooks_dir, name))

    def ensure(event, entry, needle):
        arr = hooks.setdefault(event, [])
        if not any(needle in h.get("command", "")
                   for e in arr for h in e.get("hooks", [])):
            arr.append(entry)

    ensure("SessionStart",
           {"hooks": [{"type": "command", "command": cmd("fable-trigger.py")}]},
           "fable-trigger.py")
    ensure("UserPromptSubmit",
           {"hooks": [{"type": "command", "command": cmd("fable-trigger.py")}]},
           "fable-trigger.py")
    ensure("PostToolUse",
           {"matcher": "Edit|Write|MultiEdit",
            "hooks": [{"type": "command", "command": cmd("test-after-edit.py")}]},
           "test-after-edit.py")

    json.dump(d, open(settings_path, "w"), indent=2)
    print("  settings.json updated")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("usage: merge_settings.py <settings.json> <python-exe> <hooks-dir>")
    merge(sys.argv[1], sys.argv[2], sys.argv[3])
