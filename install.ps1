#!/usr/bin/env pwsh
# Native entry point for Windows. Locates Python and runs the real,
# cross-platform installer (install.py). macOS / Linux: use ./install.sh
# (or run `python install.py` directly on any OS).
# Compatible with Windows PowerShell 5.1 and PowerShell 7+.
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Error "python (or python3) not found on PATH — required for the hooks."
    exit 1
}
& $python.Source (Join-Path $Repo "install.py") @args
exit $LASTEXITCODE
