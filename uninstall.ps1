#!/usr/bin/env pwsh
# Native uninstall entry point for Windows. Locates Python and runs uninstall.py.
# macOS / Linux: use ./uninstall.sh (or run `python uninstall.py`).
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Error "python (or python3) not found on PATH."
    exit 1
}
& $python.Source (Join-Path $Repo "uninstall.py") @args
exit $LASTEXITCODE
