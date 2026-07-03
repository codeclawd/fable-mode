#!/usr/bin/env python3
"""Dual-event hook: load the Fable execution playbook when the mode is active.

SessionStart      When the `fable` launcher declared the mode (FABLE_MODE=1):
                  sources startup/clear/compact always inject (fresh or wiped
                  context); resume injects only if this session has no marker
                  yet. This path works on every Claude Code version — it does
                  not depend on the harness exposing effort to hooks.
UserPromptSubmit  A trigger phrase ("use fable" / "fable mode" / "load fable")
                  always injects (explicit intent; re-say after a compaction).
                  Heavy effort (payload effort.level, else CLAUDE_EFFORT env)
                  or FABLE_MODE injects once per session (marker file keyed by
                  session_id) so the ~12 KB playbook isn't re-sent every prompt.

No trigger -> prints nothing -> the playbook costs zero tokens by default.
"""
import sys
import json
import re
import os
import tempfile

PLAYBOOK = os.path.expanduser(os.path.join("~", ".claude", "FABLE_PLAYBOOK.md"))
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


def fable_mode():
    return os.environ.get("FABLE_MODE", "").strip() == "1"


def marker_path(data):
    sid = str(data.get("session_id") or "nosession")
    sid = re.sub(r"[^A-Za-z0-9_-]", "_", sid)
    return os.path.join(tempfile.gettempdir(), "fable-loaded-" + sid)


def write_marker(path):
    try:
        open(path, "w").close()
    except Exception:
        pass  # marker is best-effort; worst case is one duplicate injection


def inject(event, why):
    try:
        with open(PLAYBOOK, encoding="utf-8") as f:
            body = f.read()
    except Exception:
        return  # playbook missing/unreadable: never block the session
    context = ("Fable mode active ({}). Adopt the execution playbook below as "
               "standing discipline for the rest of this session:\n\n".format(why)
               + body)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        }
    }))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # malformed input: never block the prompt

    event = str(data.get("hook_event_name") or "UserPromptSubmit")
    marker = marker_path(data)

    if event == "SessionStart":
        if not fable_mode():
            return
        source = str(data.get("source") or "startup").lower()
        if source == "resume" and os.path.exists(marker):
            return  # context usually survives a resume; don't double-inject
        write_marker(marker)
        inject("SessionStart", "launcher")
        return

    prompt = data.get("prompt", "") or ""
    phrase = bool(TRIGGER.search(prompt))
    effort = active_effort(data)
    heavy = effort in HEAVY_EFFORT or fable_mode()

    if not (phrase or heavy):
        return

    # Heavy-only trigger: inject just once per session.
    if heavy and not phrase:
        if os.path.exists(marker):
            return
        write_marker(marker)

    if phrase:
        why = "phrase"
    elif effort in HEAVY_EFFORT:
        why = "effort=" + effort
    else:
        why = "launcher"
    inject("UserPromptSubmit", why)


if __name__ == "__main__":
    main()
