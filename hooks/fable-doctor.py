#!/usr/bin/env python3
"""fable doctor: verify the Fable mode install/activation chain end to end.

Run directly or via the `fable doctor` launcher subcommand. Exit code 1 only
on hard failures (missing core files, unparseable/unregistered settings,
live-fire failure); warnings and info lines never fail the run.

Env knobs:
  FABLE_DOCTOR_SKIP_CLI=1   skip the `claude --version` probe (offline/tests)
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")

FAILS = []
WARNS = []


def ok(msg):
    print("[ok] " + msg)


def fail(msg):
    FAILS.append(msg)
    print("[!!] " + msg)


def warn(msg):
    WARNS.append(msg)
    print("[--] " + msg)


def check_python():
    if sys.version_info >= (3, 9):
        ok("python {}.{}.{}".format(*sys.version_info[:3]))
    else:
        fail("python >= 3.9 required, running {}.{}".format(*sys.version_info[:2]))


CORE_FILES = [
    "FABLE_PLAYBOOK.md",
    "fable-code.md",
    "fable-system.md",
    "ultracode.settings.json",
    os.path.join("hooks", "fable-trigger.py"),
    os.path.join("hooks", "test-after-edit.py"),
    os.path.join("shell", "fable.ps1"),
    os.path.join("shell", "fable.zsh"),
    os.path.join("skills", "fable", "SKILL.md"),
    os.path.join("agents", "grounding-verifier.md"),
]


def check_files():
    for rel in CORE_FILES:
        path = os.path.join(CLAUDE, rel)
        if os.path.isfile(path):
            ok("present: " + rel)
        else:
            fail("missing: " + path + "  (re-run install.py)")


def check_settings():
    """Hooks may live in settings.json (where install.py puts them) or in
    settings.local.json (a legitimate hand-managed location) — accept both."""
    path = os.path.join(CLAUDE, "settings.json")
    if not os.path.isfile(path):
        fail("settings.json missing (re-run install.py)")
        return
    try:
        with open(path, encoding="utf-8") as f:
            docs = [json.load(f)]
    except Exception as e:
        fail("settings.json unreadable: {}".format(e))
        return
    local = os.path.join(CLAUDE, "settings.local.json")
    if os.path.isfile(local):
        try:
            with open(local, encoding="utf-8") as f:
                docs.append(json.load(f))
        except Exception as e:
            warn("settings.local.json unreadable: {}".format(e))
    for event, needle in (("SessionStart", "fable-trigger.py"),
                          ("UserPromptSubmit", "fable-trigger.py"),
                          ("PostToolUse", "test-after-edit.py")):
        cmds = [h.get("command", "") for d in docs
                for ent in d.get("hooks", {}).get(event, [])
                for h in ent.get("hooks", [])]
        hit = next((c for c in cmds if needle in c), None)
        if not hit:
            fail("{} not registered for {} (re-run install.py)".format(needle, event))
            continue
        ok("{} registered for {}".format(needle, event))
        m = re.match(r'"([^"]+)"', hit)
        interp = m.group(1) if m else hit.split()[0]
        if not (os.path.isfile(interp) or shutil.which(interp)):
            fail("hook interpreter not found: " + interp)
    if not any(d.get("alwaysThinkingEnabled") is True for d in docs):
        warn("alwaysThinkingEnabled is off - reasoning-density lever missing")


def launcher_profile_candidates():
    """Shell startup files that may carry the fable launcher line. Static
    defaults always; live $PROFILE queries only when CLI probes are allowed
    (they spawn a shell, and profiles can live in redirected Documents)."""
    docs = os.path.join(HOME, "Documents")
    cands = [
        os.path.join(docs, "PowerShell", "Microsoft.PowerShell_profile.ps1"),
        os.path.join(docs, "WindowsPowerShell", "Microsoft.PowerShell_profile.ps1"),
        os.path.join(HOME, ".zshrc"),
        os.path.join(HOME, ".bashrc"),
    ]
    if os.environ.get("FABLE_DOCTOR_SKIP_CLI") != "1":
        for exe in ("pwsh", "powershell"):
            if shutil.which(exe):
                try:
                    out = subprocess.run([exe, "-NoProfile", "-Command", "$PROFILE"],
                                         capture_output=True, text=True, timeout=20)
                    p = out.stdout.strip()
                    if p and p not in cands:
                        cands.append(p)
                except Exception:
                    pass
    return cands


def check_launcher():
    """The most fragile link: a profile line sourcing a launcher file that no
    longer exists breaks every new shell — that is a hard failure. No line at
    all is only a warning (/fable and auto-activation work without it)."""
    found = False
    for path in launcher_profile_candidates():
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            continue
        for line in lines:
            if ("fable.ps1" not in line and "fable.zsh" not in line) \
                    or line.lstrip().startswith("#"):
                continue
            found = True
            m = re.search(r'["\']([^"\']*fable\.(?:ps1|zsh))["\']', line)
            target = os.path.expanduser(m.group(1)) if m else None
            if target and os.path.isfile(target):
                ok("launcher registered in {}".format(path))
            else:
                fail("launcher line in {} points to a missing file "
                     "(re-run install.py): {}".format(path, line.strip()))
    if not found:
        warn("no `fable` launcher line found in a shell profile - the `fable` "
             "command won't exist; /fable and auto-activation still work "
             "(re-run install.py to add it)")


def _shim_safe(exe, args):
    """npm installs claude as a .cmd shim on Windows; CreateProcess can't
    spawn those by name or path — route them through cmd.exe."""
    if exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe] + args
    return [exe] + args


def check_claude_cli():
    if os.environ.get("FABLE_DOCTOR_SKIP_CLI") == "1":
        warn("claude CLI probe skipped (FABLE_DOCTOR_SKIP_CLI=1)")
        return
    exe = shutil.which("claude")
    if not exe:
        warn("claude CLI not on PATH - the fable launcher won't start")
        return
    try:
        out = subprocess.run(_shim_safe(exe, ["--version"]), capture_output=True,
                             text=True, timeout=30).stdout.strip()
    except Exception as e:
        warn("claude --version failed: {}".format(e))
        return
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
    if not m:
        warn("could not parse claude version from: " + out)
        return
    ver = tuple(int(x) for x in m.groups())
    label = ".".join(map(str, ver))
    if ver >= (2, 1, 199):
        ok("claude {} (effort exposed to hooks)".format(label))
    else:
        warn("claude {} < 2.1.199: effort not exposed to hooks; "
             "phrase/FABLE_MODE/SessionStart paths unaffected".format(label))
    try:
        help_out = subprocess.run(_shim_safe(exe, ["--help"]), capture_output=True,
                                  text=True, timeout=30).stdout
    except Exception:
        help_out = ""
    for flag in ("--effort", "--append-system-prompt-file"):
        variants = [flag]
        if flag.endswith("-file"):
            # the CLI lists file variants as a shorthand family, e.g.
            # "--append-system-prompt[-file]"
            variants.append(flag[:-len("-file")] + "[-file]")
        if not any(v in help_out for v in variants):
            warn("claude --help does not list {} - the fable launcher may fail "
                 "on this CLI version".format(flag))


def _fire(payload, env_extra):
    hook = os.path.join(CLAUDE, "hooks", "fable-trigger.py")
    env = dict(os.environ)
    env.pop("CLAUDE_EFFORT", None)
    env.pop("FABLE_MODE", None)
    env.update(env_extra)
    p = subprocess.run([sys.executable, hook], input=json.dumps(payload),
                       capture_output=True, text=True, timeout=30, env=env)
    return p.stdout.strip()


def check_live_fire():
    if not os.path.isfile(os.path.join(CLAUDE, "hooks", "fable-trigger.py")):
        return  # already reported by check_files
    sid = "doctor-" + uuid.uuid4().hex[:8]
    try:
        ss = _fire({"hook_event_name": "SessionStart", "source": "startup",
                    "session_id": sid}, {"FABLE_MODE": "1"})
        ups = _fire({"prompt": "use fable", "session_id": sid + "-b"}, {})
    except Exception as e:
        fail("live fire errored: {}".format(e))
        return
    finally:
        for s in (sid, sid + "-b"):
            try:
                os.remove(os.path.join(tempfile.gettempdir(), "fable-loaded-" + s))
            except OSError:
                pass
    for name, out, event in (("SessionStart", ss, "SessionStart"),
                             ("UserPromptSubmit phrase", ups, "UserPromptSubmit")):
        try:
            payload = json.loads(out)["hookSpecificOutput"]
            assert payload["hookEventName"] == event
            assert "Fable mode active" in payload["additionalContext"]
            ok("live fire: {} injects".format(name))
        except Exception:
            fail("live fire: {} produced no/invalid injection: {!r}".format(
                name, out[:80]))


def check_evidence():
    files = glob.glob(os.path.join(CLAUDE, "projects", "*", "*.jsonl"))
    files.sort(key=os.path.getmtime, reverse=True)
    for path in files[:10]:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "Fable mode active" in line:
                        ok("injection seen in a recent session: "
                           + os.path.basename(path))
                        return
        except OSError:
            continue
    warn("no injection found in the 10 most recent transcripts "
         "(fine if you haven't used fable yet)")


def main():
    print("fable doctor - checking " + CLAUDE)
    check_python()
    check_files()
    check_settings()
    check_launcher()
    check_claude_cli()
    check_live_fire()
    check_evidence()
    print()
    if FAILS:
        print("RESULT: {} failure(s), {} warning(s) - Fable mode will not work "
              "correctly.".format(len(FAILS), len(WARNS)))
        sys.exit(1)
    print("RESULT: healthy ({} warning(s)).".format(len(WARNS)))


if __name__ == "__main__":
    main()
