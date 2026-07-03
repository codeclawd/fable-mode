#!/usr/bin/env python3
"""Dual-event hook: load the Fable execution playbook when the mode is active.

SessionStart      When the `fable` launcher declared the mode (FABLE_MODE=1):
                  sources startup/clear/compact always inject (fresh or wiped
                  context); resume injects only if this session has no marker
                  yet. This path works on every Claude Code version — it does
                  not depend on the harness exposing effort to hooks.
                  Without FABLE_MODE, the session marker still matters: on
                  compact it proves the mode was active (auto/effort path), so
                  the playbook is re-injected into the wiped context; on clear
                  the marker is dropped so the once-per-session paths re-arm.
UserPromptSubmit  A trigger phrase ("use fable" / "fable mode" / "load fable")
                  always injects (explicit intent; re-say after a compaction).
                  Heavy effort (payload effort.level, else CLAUDE_EFFORT env),
                  FABLE_MODE, or a task-shaped prompt (looks_complex heuristic;
                  disable with FABLE_AUTO=0) injects once per session (marker
                  file keyed by session_id) — and not at all if the transcript
                  shows the /fable skill already activated this session.

No trigger -> prints nothing -> the playbook costs zero tokens by default.
"""
import sys
import glob
import json
import re
import os
import tempfile
import time

PLAYBOOK = os.path.expanduser(os.path.join("~", ".claude", "FABLE_PLAYBOOK.md"))
TRIGGER = re.compile(r"\b(use fable|fable mode|load fable)\b", re.I)
HEAVY_EFFORT = {"xhigh", "max", "ultracode"}

# Auto-activation heuristic: score-based guess that a prompt is a real
# engineering task. >= 2 points = complex. Disable with FABLE_AUTO=0.
TASK_VERBS = re.compile(
    r"\b(implement|refactor|migrat\w*|build|creat\w*|add|fix|debug|integrat\w*|"
    r"optimi[sz]\w*|rewrit\w*|design|install|set up|updat\w*|upgrad\w*|"
    r"remov\w*|delet\w*|deploy\w*|renam\w*|writ\w*"
    r"|сдела\w*|добав\w*|почин\w*|исправ\w*|реализу\w*|перепиш\w*|настро\w*|"
    r"созда\w*|собер\w*|интегрир\w*|оптимизир\w*|мигрир\w*|разработ\w*|"
    r"удал\w*|обнов\w*|напиш\w*|запуст\w*|перенес\w*|убер\w*)", re.I)
MULTISTEP = re.compile(r"\b(затем|потом|после этого|then|steps?)\b|^\s*\d+[.)]\s",
                       re.I | re.M)
PATHISH = re.compile(
    r"\w+\.(py|js|ts|tsx|java|go|rs|c|cpp|h|cs|rb|php|md|json|ya?ml|toml|ps1|sh|zsh)\b"
    r"|[/\\][\w.-]+[/\\]")
FENCE_OR_TRACE = re.compile(r"```|Traceback \(most recent call last\)|^\s*File \"",
                            re.M)


def looks_complex(prompt):
    score = 0
    if len(prompt) >= 400:
        score += 2
    if FENCE_OR_TRACE.search(prompt):
        score += 2
    score += min(len(set(m.group(0).lower() for m in TASK_VERBS.finditer(prompt))), 2)
    if PATHISH.search(prompt):
        score += 1
    if MULTISTEP.search(prompt):
        score += 1
    if len([ln for ln in prompt.splitlines() if ln.strip()]) >= 3:
        score += 1
    return score >= 2


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
    prune_stale_markers()


def prune_stale_markers():
    """Best-effort GC: a week-old session marker belongs to a dead session.
    Windows never clears %TEMP%, so without this they accumulate forever."""
    cutoff = time.time() - 7 * 86400
    for p in glob.glob(os.path.join(tempfile.gettempdir(), "fable-loaded-*")):
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
        except OSError:
            pass


def transcript_has_activation(data):
    """True if this session's transcript already contains a Fable activation —
    either a previous injection or the /fable skill's confirmation line."""
    path = data.get("transcript_path") or ""
    if not path or not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return any("Fable mode active" in line for line in f)
    except OSError:
        return False


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
        source = str(data.get("source") or "startup").lower()
        if fable_mode():
            if source == "resume" and os.path.exists(marker):
                return  # context usually survives a resume; don't double-inject
            write_marker(marker)
            inject("SessionStart", "launcher")
            return
        # No launcher declaration. The marker is the proof that this session
        # activated via the auto/effort/FABLE_MODE path earlier:
        if source == "compact" and os.path.exists(marker):
            inject("SessionStart", "compact")  # compaction wiped it; restore
        elif source == "clear":
            try:
                os.remove(marker)  # fresh context: re-arm once-per-session paths
            except OSError:
                pass
        return

    prompt = data.get("prompt", "") or ""
    phrase = bool(TRIGGER.search(prompt))
    effort = active_effort(data)
    auto = os.environ.get("FABLE_AUTO", "").strip() != "0" and looks_complex(prompt)
    heavy = effort in HEAVY_EFFORT or fable_mode() or auto

    if not (phrase or heavy):
        return

    # Heavy-only trigger: inject just once per session. A "Fable mode active"
    # line already in the transcript means the /fable skill (or an earlier
    # injection) activated this session — don't add a duplicate playbook.
    if heavy and not phrase:
        if os.path.exists(marker):
            return
        write_marker(marker)
        if transcript_has_activation(data):
            return

    if phrase:
        why = "phrase"
    elif effort in HEAVY_EFFORT:
        why = "effort=" + effort
    elif fable_mode():
        why = "launcher"
    else:
        why = "auto"
    inject("UserPromptSubmit", why)


if __name__ == "__main__":
    main()
