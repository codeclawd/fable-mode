# Fable mode launcher (PowerShell). Dot-source from your profile, or:
#   . C:\path\to\fable-mode\shell\fable.ps1
#
# `fable`          Claude Code pinned to Opus 4.8, Fable Claude-Code behavior
#                  layer appended, xhigh effort, FABLE_MODE=1 declared so
#                  fable-trigger.py injects the playbook at SessionStart.
# `fable --ultra`  Same, plus ultracode: the harness auto-runs multi-agent
#                  workflows for substantive tasks (heavy on tokens).
# `fable doctor`   Verify the whole install/activation chain mechanically.
#
# install.ps1 copies fable-code.md and fable-doctor.py into ~\.claude for you.
function fable {
    $rest = @($args)
    if ($rest.Count -gt 0 -and $rest[0] -eq 'doctor') {
        & python "$HOME\.claude\hooks\fable-doctor.py" @($rest | Select-Object -Skip 1)
        return
    }
    $extra = @()
    if ($rest.Count -gt 0 -and ($rest[0] -eq '--ultra' -or $rest[0] -eq '-u')) {
        $rest = @($rest | Select-Object -Skip 1)
        $extra = @('--settings', '{"ultracode": true}')
    }
    $env:FABLE_MODE = "1"
    try {
        claude --model claude-opus-4-8 `
            --append-system-prompt-file "$HOME\.claude\fable-code.md" `
            --effort xhigh @extra @rest
    }
    finally {
        Remove-Item Env:FABLE_MODE -ErrorAction SilentlyContinue
    }
}
