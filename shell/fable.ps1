# Fable mode launcher (PowerShell). Dot-source from your profile, or:
#   . C:\path\to\fable-mode\shell\fable.ps1
#
# Launches Claude Code (Opus 4.8) with the Fable 5 system prompt appended and
# ultracode effort (sends xhigh to the model AND auto-orchestrates multi-agent
# workflows for substantive tasks — the heaviest mode). ultracode is session-only,
# so it's set via --settings, not --effort. It also trips fable-trigger.py, which
# layers FABLE_PLAYBOOK execution discipline on top.
#
# install.ps1 copies fable-system.md into ~\.claude for you.
# If ultracode's auto-workflows burn too many tokens, swap --settings for --effort xhigh.
function fable {
    claude --append-system-prompt-file "$HOME\.claude\fable-system.md" --settings '{"ultracode": true}' @args
}
