#!/usr/bin/env python3
"""UserPromptSubmit hook: two-layer Fable injection.

Layer 1 — FABLE_CODE.md (native Claude Code distillation): injected ONCE per
session, on the first prompt, unconditionally. This is the always-on
disposition layer; it is sized to fit the documented 10,000-character cap on
hook additionalContext (only the rules section above its "## Relationship"
divider is injected).

Layer 2 — FABLE_PLAYBOOK.md (measured layer, ~21 KB): OVER the 10k cap, so it
is never inlined — inlining it makes Claude Code degrade the hook output to a
file-path preview. Instead, on a trigger phrase ("use fable" / "fable mode" /
"load fable") or heavy effort (xhigh/max/ultracode) the hook injects a
directive to Read the file. Phrase always fires (re-say after a compaction);
the effort path fires once per session.

Effort comes from the hook payload (effort.level or effort string) with the
CLAUDE_EFFORT env var as fallback — both documented at
code.claude.com/docs/en/hooks.

If ~/.claude/docs/LOOP-HARNESS.md exists (loop-harness-system installed), the
first-prompt injection adds a one-line bridge pointing at it.

Knobs (env):
  FABLE_DISABLE=1         disable this hook entirely
  FABLE_CODE_APPENDED=1   skip layer 1 (the `fable` launcher sets this — it
                          already appends FABLE_CODE.md to the system prompt)

Safety: always exits 0, never blocks the prompt.
"""
import sys
import json
import re
import os
import tempfile

CLAUDE = os.path.expanduser(os.path.join("~", ".claude"))
CODE = os.path.join(CLAUDE, "FABLE_CODE.md")
PLAYBOOK = os.path.join(CLAUDE, "FABLE_PLAYBOOK.md")
HARNESS = os.path.join(CLAUDE, "docs", "LOOP-HARNESS.md")

TRIGGER = re.compile(r"\b(use fable|fable mode|load fable)\b", re.I)
HEAVY_EFFORT = {"xhigh", "max", "ultracode"}
# The documented cap is 10,000 chars for the whole additionalContext string;
# stay under it with headroom for the preamble/bridge lines.
CAP = 9800
# Everything below this divider in FABLE_CODE.md is for human readers of the
# repo, not for injection.
CODE_SPLIT = "## Relationship to the rest of the bundle"


def active_effort(data):
    """Effort from the hook JSON (effort.level or effort string), else env."""
    eff = data.get("effort")
    if isinstance(eff, dict):
        eff = eff.get("level")
    if not eff:
        eff = os.environ.get("CLAUDE_EFFORT", "")
    return str(eff).strip().lower()


def marker(kind, sid):
    sid = re.sub(r"[^A-Za-z0-9_-]", "_", str(sid or "nosession"))
    return os.path.join(tempfile.gettempdir(), f"fable-{kind}-{sid}")


def seen(kind, sid):
    """True if this layer already fired for the session; else stamp it."""
    path = marker(kind, sid)
    if os.path.exists(path):
        return True
    try:
        open(path, "w").close()
    except Exception:
        pass
    return False


def read_code_rules():
    """FABLE_CODE.md up to its human-readers divider, or None."""
    try:
        with open(CODE, encoding="utf-8") as f:
            body = f.read()
    except Exception:
        return None
    idx = body.find(CODE_SPLIT)
    return (body[:idx] if idx > 0 else body).rstrip().rstrip("-").rstrip()


def main():
    if os.environ.get("FABLE_DISABLE"):
        return
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # malformed input: never block the prompt

    # Docs have used both field names for the submitted text.
    prompt = data.get("prompt") or data.get("user_prompt") or ""
    sid = data.get("session_id")
    phrase = bool(TRIGGER.search(prompt))
    effort = active_effort(data)
    effort_heavy = effort in HEAVY_EFFORT

    parts = []

    # Layer 1: always-on disposition, first prompt of the session only.
    # Skipped when the `fable` launcher already appended it to the system prompt.
    if not os.environ.get("FABLE_CODE_APPENDED") and not seen("code", sid):
        rules = read_code_rules()
        if rules:
            parts.append(
                "Fable mode: adopt the following as standing discipline for "
                "this entire session.\n\n" + rules
            )
            if os.path.isfile(HARNESS):
                parts.append(
                    "loop-harness-system is installed: for any long-running "
                    "build, follow ~/.claude/docs/LOOP-HARNESS.md "
                    "(contract-first, fresh-context evaluation, 3-file state; "
                    "skills: loop-lane, app-forge, verify-app, design-lane)."
                )

    # Layer 2: the measured playbook, by directive (it exceeds the inline cap).
    want_playbook = phrase or (effort_heavy and not seen("playbook", sid))
    if want_playbook and os.path.isfile(PLAYBOOK):
        why = "trigger phrase" if phrase else "effort=" + effort
        parts.append(
            f"Fable heavy mode ({why}): before other work, Read "
            f"{PLAYBOOK} with the Read tool and adopt it as standing "
            "discipline for the rest of the session. It is ~21 KB — too "
            "large to inject inline here — so reading it yourself is the "
            "load, not an optional reference."
        )
        if phrase:
            # A phrase implies the user wants the full stack now; make sure
            # the effort path doesn't re-fire later in this session.
            seen("playbook", sid)

    if not parts:
        return

    context = "\n\n".join(parts)
    if len(context) > CAP:  # never let the harness degrade this to a file preview
        context = context[:CAP].rsplit("\n", 1)[0] + "\n[truncated to fit hook cap]"

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))


if __name__ == "__main__":
    main()
