# Fable mode launcher (PowerShell). Dot-source from your profile, or:
#   . C:\path\to\fable-mode\shell\fable.ps1
#
# Launches Claude Code pinned to Opus 4.8 with the Fable Claude-Code behavior
# layer appended and xhigh effort, and declares the mode via FABLE_MODE=1 so
# fable-trigger.py injects the execution playbook at SessionStart — reliable on
# every Claude Code version, not only those that expose effort to hooks.
#
# install.ps1 copies fable-code.md into ~\.claude for you.
# Want multi-agent auto-orchestration too? Add: --settings '{"ultracode": true}'
function fable {
    $env:FABLE_MODE = "1"
    try {
        claude --model claude-opus-4-8 `
            --append-system-prompt-file "$HOME\.claude\fable-code.md" `
            --effort xhigh @args
    }
    finally {
        Remove-Item Env:FABLE_MODE -ErrorAction SilentlyContinue
    }
}
