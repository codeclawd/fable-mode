# Contributing to fable-mode

Thanks for helping! fable-mode is deliberately small and cross-platform. A few
conventions keep it that way.

## Development setup

```sh
git clone https://github.com/HalalifyMusic/fable-mode
cd fable-mode
python -m pip install --upgrade pytest
python -m pytest -q
```

Requires Python ≥ 3.9. The hooks and the installer are **stdlib-only** — keep them
dependency-free so they run in any Claude Code environment without a pip install.

## Layout

- `install.py` — the real installer; `install.sh` / `install.ps1` just locate
  Python and exec it. `uninstall.py` mirrors it (with the same wrappers).
- `scripts/merge_settings.py` — shared `settings.json` merge (importable + CLI).
- `hooks/` — `fable-trigger.py` (playbook injection) and `test-after-edit.py` (run
  tests after an edit). Both must exit 0 and never block a prompt or an edit.
- `shell/` — `fable.zsh` (Unix) and `fable.ps1` (PowerShell) launchers.
- `skills/`, `agents/` — bundled skills and the grounding-verifier agent.
- `tests/` — pytest for the hooks and the installer.

## Rules of the road

- **Cross-platform first.** Anything touching paths, shells, or subprocesses must
  work on Windows, macOS, and Linux. CI runs the suite on all three.
- **Add tests.** Changes to a hook or the installer need matching tests in
  `tests/`. Keep them hermetic — use `tmp_path` and the host interpreter, no
  Node / make / network.
- **Don't fight line endings.** `.gitattributes` enforces LF for shell/Python and
  CRLF for PowerShell. Let it; `.editorconfig` matches.
- **Leave vendored content alone.** The Anthropic skills under `skills/` and
  `fable-system.md` are upstream copies — fix those upstream, not here.
- Match the surrounding style and keep diffs focused.

## Pull requests

1. Branch off `main`.
2. `python -m pytest -q` green locally.
3. Describe what changed and why; note any platform-specific behavior.
4. CI must pass on ubuntu/macos/windows before merge.

See [SECURITY.md](SECURITY.md) for the security model and how to report issues, and
[CHANGELOG.md](CHANGELOG.md) for the running history.
