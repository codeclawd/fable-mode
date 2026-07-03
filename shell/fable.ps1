# Fable mode launcher (PowerShell). Dot-source from your profile, or:
#   . C:\path\to\fable-mode\shell\fable.ps1
#
# Launches Claude Code (Opus 4.8) with the Fable 5 system prompt appended and
# xhigh effort — the heavy-reasoning lever that closes part of the measured
# 70-vs-47 reasoning-density gap prose alone can't. It also trips fable-trigger.py,
# which layers FABLE_PLAYBOOK execution discipline on top.
#
# install.ps1 copies fable-system.md into ~\.claude for you.
# Want multi-agent auto-orchestration too? Swap `--effort xhigh` for
# `--settings '{"ultracode": true}'` — that sends xhigh AND auto-runs workflows for
# substantive tasks (the heaviest mode, and heavier on tokens).
function fable {
    claude --append-system-prompt-file "$HOME\.claude\fable-system.md" --effort xhigh @args
}
