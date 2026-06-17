#!/usr/bin/env python3
"""UserPromptSubmit hook: load the Fable execution playbook on demand.

Injects FABLE_PLAYBOOK.md into the turn's context when EITHER:
  - the user's message contains a trigger phrase ("use fable" / "fable mode" /
    "load fable"), or
  - the active effort level is xhigh/max (so heavy mode follows the effort lever
    without needing a phrase).

The phrase path always injects (explicit intent; re-say after a compaction). The
effort path injects ONCE per session (marker file keyed by session_id) so it
doesn't re-inject the 12 KB playbook on every prompt. No phrase + low effort ->
nothing injected, so the playbook costs zero tokens by default.
"""
import sys
import json
import re
import os
import tempfile

PLAYBOOK = "/Users/ak/FABLE_PLAYBOOK.md"
TRIGGER = re.compile(r"\b(use fable|fable mode|load fable)\b", re.I)
HEAVY_EFFORT = {"xhigh", "max", "ultracode"}


def active_effort(data):
    """Effort from the hook JSON (effort.level or effort string), else env."""
    eff = data.get("effort")
    if isinstance(eff, dict):
        eff = eff.get("level")
    if not eff:
        eff = os.environ.get("CLAUDE_EFFORT", "")
    return str(eff).strip().lower()


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # malformed input: never block the prompt

    prompt = data.get("prompt", "") or ""
    phrase = bool(TRIGGER.search(prompt))
    effort_heavy = active_effort(data) in HEAVY_EFFORT

    if not (phrase or effort_heavy):
        return

    # Effort-only trigger: inject just once per session.
    if effort_heavy and not phrase:
        sid = str(data.get("session_id") or "nosession")
        sid = re.sub(r"[^A-Za-z0-9_-]", "_", sid)
        marker = os.path.join(tempfile.gettempdir(), f"fable-loaded-{sid}")
        if os.path.exists(marker):
            return
        try:
            open(marker, "w").close()
        except Exception:
            pass

    try:
        with open(PLAYBOOK, encoding="utf-8") as f:
            body = f.read()
    except Exception:
        return

    why = "phrase" if phrase else "effort=" + active_effort(data)
    context = (f"Fable mode active ({why}). Adopt the execution playbook below as "
               "standing discipline for the rest of this session:\n\n" + body)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))


if __name__ == "__main__":
    main()
