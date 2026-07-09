#!/usr/bin/env python3
"""Dual-event hook: inject the Fable disposition + playbook when active.

SessionStart      When the `fable` launcher declared the mode (FABLE_MODE=1):
                  FABLE_CODE.md rules + a playbook Read directive on
                  startup/clear/compact always fire (fresh or wiped context);
                  resume fires only if this session has no marker yet.
                  Without FABLE_MODE, the session marker still matters: on
                  compact it proves the mode was active (auto/effort path), so
                  both layers re-inject into the wiped context; on clear the
                  marker is dropped so the once-per-session paths re-arm.
UserPromptSubmit  Layer 1 — FABLE_CODE.md rules (the always-on disposition,
                  ~10k, under the hook cap): injected ONCE per session on the
                  first prompt, unconditionally. Skipped when the `fable`
                  launcher already appended it (FABLE_CODE_APPENDED=1).
                  Layer 2 — FABLE_PLAYBOOK.md (~21k, over the cap): never
                  inlined (Claude Code degrades >10k hook output to a file-path
                  preview). A Read directive is injected on trigger phrase
                  ("use fable"/"fable mode"/"load fable"), heavy effort
                  (xhigh/max/ultracode), FABLE_MODE, or a task-shaped prompt
                  (looks_complex heuristic; disable with FABLE_AUTO=0) — once
                  per session (marker file keyed by session_id), and not at all
                  if the transcript shows the /fable skill already activated.

No trigger -> prints nothing -> zero tokens by default. Always exits 0.
"""
import sys
import glob
import json
import re
import os
import tempfile
import time

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


def marker(kind, sid):
    sid = re.sub(r"[^A-Za-z0-9_-]", "_", str(sid or "nosession"))
    return os.path.join(tempfile.gettempdir(), "fable-{}-{}".format(kind, sid))


def seen(kind, sid):
    """True if this layer already fired for the session; else stamp it."""
    path = marker(kind, sid)
    if os.path.exists(path):
        return True
    try:
        open(path, "w").close()
    except Exception:
        pass
    prune_stale_markers()
    return False


def prune_stale_markers():
    """Best-effort GC: week-old markers belong to dead sessions.
    Windows never clears %TEMP%, so without this they accumulate forever."""
    cutoff = time.time() - 7 * 86400
    for p in glob.glob(os.path.join(tempfile.gettempdir(), "fable-*-")):
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
        except OSError:
            pass


def read_code_rules():
    """FABLE_CODE.md up to its human-readers divider, or None."""
    try:
        with open(CODE, encoding="utf-8") as f:
            body = f.read()
    except Exception:
        return None
    idx = body.find(CODE_SPLIT)
    return (body[:idx] if idx > 0 else body).rstrip().rstrip("-").rstrip()


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


def emit(event, context):
    """Print a hook additionalContext payload, capped at CAP chars."""
    if len(context) > CAP:
        context = context[:CAP].rsplit("\n", 1)[0] + "\n[truncated to fit hook cap]"
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        }
    }))


def playbook_directive(why):
    """A Read directive for FABLE_PLAYBOOK.md — never inlined (it exceeds the
    10k hook cap; inlining makes Claude Code degrade it to a file-path preview)."""
    if not os.path.isfile(PLAYBOOK):
        return None
    return ("Fable heavy mode ({}): before other work, Read "
            "{} with the Read tool and adopt it as standing "
            "discipline for the rest of this session. It is ~21 KB — too "
            "large to inject inline here — so reading it yourself is the "
            "load, not an optional reference.".format(why, PLAYBOOK))


def code_rules_block():
    """The always-on FABLE_CODE.md rules injection."""
    rules = read_code_rules()
    if not rules:
        return None
    parts = [
        "Fable mode active: adopt the following as standing discipline for "
        "this entire session.\n\n" + rules
    ]
    if os.path.isfile(HARNESS):
        parts.append(
            "loop-harness-system is installed: for any long-running "
            "build, follow ~/.claude/docs/LOOP-HARNESS.md "
            "(contract-first, fresh-context evaluation, 3-file state; "
            "skills: loop-lane, app-forge, verify-app, design-lane)."
        )
    return "\n\n".join(parts)


def handle_session_start(data, sid):
    """SessionStart event: inject both layers if the mode is active."""
    source = str(data.get("source") or "startup").lower()
    code_appended = os.environ.get("FABLE_CODE_APPENDED")
    fm = fable_mode()

    if fm:
        # Launcher declared the mode. startup/clear/compact always inject;
        # resume injects only if no marker yet (context usually survives).
        if source == "resume" and os.path.exists(marker("code", sid)):
            return
        parts = []
        if not code_appended and not seen("code", sid):
            block = code_rules_block()
            if block:
                parts.append(block)
        # Always issue the playbook Read directive at session start when
        # the launcher is active — the playbook is the measured layer.
        directive = playbook_directive("launcher")
        if directive:
            parts.append(directive)
        if parts:
            emit("SessionStart", "\n\n".join(parts))
        return

    # No launcher declaration. The marker is the proof that this session
    # activated via the auto/effort/FABLE_MODE path earlier:
    if source == "compact":
        had_code = os.path.exists(marker("code", sid))
        had_playbook = os.path.exists(marker("playbook", sid))
        if had_code or had_playbook:
            parts = []
            if had_code and not code_appended:
                block = code_rules_block()
                if block:
                    parts.append(block)
            if had_playbook:
                directive = playbook_directive("compact")
                if directive:
                    parts.append(directive)
            if parts:
                emit("SessionStart", "\n\n".join(parts))
    elif source == "clear":
        for kind in ("code", "playbook"):
            try:
                os.remove(marker(kind, sid))
            except OSError:
                pass


def stamp_marker(kind, sid):
    """Write the marker file without checking (fire-and-stamp)."""
    path = marker(kind, sid)
    try:
        open(path, "w").close()
    except Exception:
        pass
    prune_stale_markers()


def handle_prompt_submit(data, sid):
    """UserPromptSubmit event: two-layer injection."""
    prompt = data.get("prompt") or data.get("user_prompt") or ""
    phrase = bool(TRIGGER.search(prompt))
    effort = active_effort(data)
    effort_heavy = effort in HEAVY_EFFORT
    fm = fable_mode()
    auto = os.environ.get("FABLE_AUTO", "").strip() != "0" and looks_complex(prompt)
    seen_playbook = os.path.exists(marker("playbook", sid))

    parts = []

    # Layer 1: always-on disposition, first prompt of the session only.
    # Skipped when the `fable` launcher already appended it to the system prompt.
    if not os.environ.get("FABLE_CODE_APPENDED") and not seen("code", sid):
        block = code_rules_block()
        if block:
            parts.append(block)

    # Layer 2: the measured playbook, by directive (it exceeds the inline cap).
    # 'phrase' always fires; 'heavy' fires once per session unless already
    # activated via /fable skill (detected in transcript).
    heavy = effort_heavy or fm or auto
    playbook_needed = False
    playbook_why = None
    if phrase:
        playbook_needed = True
        playbook_why = "trigger phrase"
    elif heavy:
        if not seen_playbook and not transcript_has_activation(data):
            playbook_needed = True
            playbook_why = ("effort=" + effort) if effort_heavy else (
                            "launcher" if fm else "auto")
        # Stamp the marker for the heavy path regardless (it fired or was
        # already active — don't let it re-fire next prompt).
        if not seen_playbook:
            stamp_marker("playbook", sid)

    if playbook_needed:
        directive = playbook_directive(playbook_why)
        if directive:
            parts.append(directive)

    if not parts:
        return

    emit("UserPromptSubmit", "\n\n".join(parts))


def main():
    if os.environ.get("FABLE_DISABLE"):
        return
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # malformed input: never block the prompt

    event = str(data.get("hook_event_name") or "UserPromptSubmit")
    sid = data.get("session_id")

    if event == "SessionStart":
        handle_session_start(data, sid)
    else:
        handle_prompt_submit(data, sid)


if __name__ == "__main__":
    main()
