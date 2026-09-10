# Fable mode launcher (PowerShell). install.py copies this file to
# ~\.claude\shell\fable.ps1 and dot-sources it from your $PROFILE, so the
# cloned repo can be moved or deleted after install. Manual use:
#   . $HOME\.claude\shell\fable.ps1
#
# `fable`          Claude Code on Fable 5.1 ($env:FABLE_MODEL overrides), FABLE_CODE.md (native Claude
#                  Code distillation) appended, xhigh effort, FABLE_MODE=1
#                  declared so fable-trigger.py injects the playbook at
#                  SessionStart.
# `fable --ultra`  Same, plus ultracode: the harness auto-runs multi-agent
#                  workflows for substantive tasks (heavy on tokens).
# `fable doctor`   Verify the whole install/activation chain mechanically.
function fable {
    $rest = @($args)
    if ($rest.Count -gt 0 -and $rest[0] -eq 'doctor') {
        # Not every Windows box has `python` on PATH; try the common launchers.
        $py = $null
        foreach ($cand in 'python', 'py', 'python3') {
            if (Get-Command $cand -ErrorAction SilentlyContinue) { $py = $cand; break }
        }
        if (-not $py) {
            Write-Error 'Python not found on PATH - cannot run fable doctor.'
            return
        }
        & $py "$HOME\.claude\hooks\fable-doctor.py" @($rest | Select-Object -Skip 1)
        return
    }
    $extra = @()
    if ($rest.Count -gt 0 -and ($rest[0] -eq '--ultra' -or $rest[0] -eq '-u')) {
        $rest = @($rest | Select-Object -Skip 1)
        # A file path, not inline JSON: Windows PowerShell 5.1 strips the inner
        # quotes when building the native command line, so {"ultracode": true}
        # reaches claude as {ultracode: true} - "Invalid JSON provided for
        # --settings" (issue #2). A path survives quoting on every PS version.
        $extra = @('--settings', "$HOME\.claude\shell\ultracode.settings.json")
    }
    $env:FABLE_MODE = "1"
    try {
        $model = if ($env:FABLE_MODEL) { $env:FABLE_MODEL } else { 'claude-fable-5-1' }
        claude --model $model `
            --append-system-prompt-file "$HOME\.claude\FABLE_CODE.md" `
            --effort xhigh @extra @rest
    }
    finally {
        Remove-Item Env:FABLE_MODE -ErrorAction SilentlyContinue
    }
}
