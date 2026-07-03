"""Launcher regression tests for issue #2: inline JSON passed to --settings is
mangled by PowerShell 5.1's native-argument quoting ({"ultracode": true} arrives
as {ultracode: true}). The launchers must therefore never pass inline JSON —
only a settings *file path*, which survives quoting in every shell."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def test_ultracode_settings_file_is_valid_json():
    data = json.loads((REPO / "shell" / "ultracode.settings.json").read_text(encoding="utf-8"))
    assert data == {"ultracode": True}


def test_launchers_pass_no_inline_json():
    for name in ("fable.zsh", "fable.ps1"):
        text = (REPO / "shell" / name).read_text(encoding="utf-8")
        assert "--settings '{" not in text and '--settings "{' not in text, (
            f"{name} passes inline JSON to --settings; PowerShell 5.1 strips the "
            "inner quotes (issue #2) — pass the settings file path instead")
        assert "ultracode.settings.json" in text, f"{name} should use the settings file"


def test_ps1_doctor_resolves_python_fallback():
    """`python` isn't guaranteed on Windows PATH — the doctor subcommand must
    fall back across the common launcher names instead of failing outright."""
    text = (REPO / "shell" / "fable.ps1").read_text(encoding="utf-8")
    for cand in ("'python'", "'py'", "'python3'"):
        assert cand in text, f"fable doctor should try {cand} on PATH"


@pytest.mark.skipif(os.name != "nt" or not shutil.which("powershell"),
                    reason="Windows PowerShell 5.1 only exists on Windows; on "
                           "macOS/Linux runners `powershell` is just pwsh")
def test_ultra_flag_survives_powershell51(tmp_path):
    """Drive the real fable.ps1 through powershell.exe with a fake claude.cmd and
    assert the --settings argument arrives brace-free (i.e. a file path)."""
    capture = tmp_path / "argv.txt"
    fake = tmp_path / "claude.cmd"
    fake.write_text("@echo off\r\necho %*> \"%CAPTURE%\"\r\n", encoding="ascii")
    ps1 = REPO / "shell" / "fable.ps1"
    cmd = (f"$env:PATH = '{tmp_path};' + $env:PATH; "
           f"$env:CAPTURE = '{capture}'; "
           f". '{ps1}'; fable --ultra")
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=60)
    argv = capture.read_text(encoding="utf-8", errors="ignore")
    assert "--settings" in argv, (p.stdout, p.stderr)
    assert "{" not in argv, f"inline JSON leaked through (issue #2): {argv!r}"
    assert "ultracode.settings.json" in argv
