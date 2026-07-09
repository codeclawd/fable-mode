# Fable mode launcher (PowerShell). install.py copies this file to\r
# ~\.claude\shell\fable.ps1 and dot-sources it from your $PROFILE, so the\r
# cloned repo can be moved or deleted after install. Manual use:\r
#   . $HOME\.claude\shell\fable.ps1\r
#\r
# `fable`          Claude Code pinned to Opus 4.8, FABLE_CODE.md (native Claude\r
#                  Code distillation) appended, xhigh effort, FABLE_MODE=1\r
#                  declared so fable-trigger.py injects the playbook at\r
#                  SessionStart.\r
# `fable --ultra`  Same, plus ultracode: the harness auto-runs multi-agent\r
#                  workflows for substantive tasks (heavy on tokens).\r
# `fable doctor`   Verify the whole install/activation chain mechanically.\r
function fable {\r
    $rest = @($args)\r
    if ($rest.Count -gt 0 -and $rest[0] -eq 'doctor') {\r
        # Not every Windows box has `python` on PATH; try the common launchers.\r
        $py = $null\r
        foreach ($cand in 'python', 'py', 'python3') {\r
            if (Get-Command $cand -ErrorAction SilentlyContinue) { $py = $cand; break }\r
        }\r
        if (-not $py) {\r
            Write-Error 'Python not found on PATH - cannot run fable doctor.'\r
            return\r
        }\r
        & $py "$HOME\.claude\hooks\fable-doctor.py" @($rest | Select-Object -Skip 1)\r
        return\r
    }\r
    $extra = @()\r
    if ($rest.Count -gt 0 -and ($rest[0] -eq '--ultra' -or $rest[0] -eq '-u')) {\r
        $rest = @($rest | Select-Object -Skip 1)\r
        # A file path, not inline JSON: Windows PowerShell 5.1 strips the inner\r
        # quotes when building the native command line, so {"ultracode": true}\r
        # reaches claude as {ultracode: true} - "Invalid JSON provided for\r
        # --settings" (issue #2). A path survives quoting on every PS version.\r
        $extra = @('--settings', "$HOME\.claude\shell\ultracode.settings.json")\r
    }\r
    $env:FABLE_MODE = "1"\r
    try {\r
        claude --model claude-opus-4-8 `\r
            --append-system-prompt-file "$HOME\.claude\FABLE_CODE.md" `\r
            --effort xhigh @extra @rest\r
    }\r
    finally {\r
        Remove-Item Env:FABLE_MODE -ErrorAction SilentlyContinue\r
    }\r
}\r
