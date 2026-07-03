# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- The playbook injector never actually fired: the effort path needs `effort` in
  the hook payload or `CLAUDE_EFFORT` in the hook environment, which Claude Code
  ≤ 2.1.198 did not provide, and the trigger phrases were undiscoverable. The
  launcher now declares the mode via `FABLE_MODE=1` and `fable-trigger.py`
  became dual-event — SessionStart injection (version-independent) plus the old
  phrase/effort paths and a `FABLE_MODE` fallback on UserPromptSubmit.
- `merge_settings.py` overwrote `settings.json.bak` on every install run, so a
  second install destroyed the pristine pre-install backup (contradicting the
  "safe to re-run" promise). It now writes that backup only when absent, keeping
  the original restore point intact.
- Closed leaked file handles (`json.load(open(...))` / `json.dump(..., open(...))`)
  in `merge_settings.py`, `uninstall.py`, and `test-after-edit.py` — they now use
  `with` blocks, which also avoids file-lock surprises on Windows.
- `fable-trigger.py` read the playbook from a hardcoded `/Users/ak/...` path, so
  on-demand injection silently failed for everyone but the original author. It now
  resolves `~/.claude/FABLE_PLAYBOOK.md`.
- `test-after-edit.py` was a silent no-op on Windows — the `npm`/`pnpm`/`yarn`/
  `make` shims raised `FileNotFoundError`. It now resolves the runner via
  `shutil.which` and runs through `cmd.exe` on Windows. Also dropped a duplicate
  `.lockb` skip entry.

### Added
- `fable-code.md`: an original Claude Code-native Fable behavior layer; the
  launcher appends it instead of the 1,600-line consumer prompt (which stays
  bundled for reference).
- `/fable` skill for explicit mid-session activation.
- The launcher pins `--model claude-opus-4-8`, making the README's "runs on
  Opus 4.8" promise true regardless of the user's default model.
- Round-trip uninstall test (`tests/test_uninstall.py`).
- `test-after-edit.py` gained a `FABLE_TEST_HOOK_ALLOW` allowlist (os.pathsep-
  separated trusted root prefixes) so the auto-run test hook can be confined to
  repositories you trust, plus a per-project `.fable-test` file to pin the exact
  command it runs (e.g. a fast, scoped command instead of the whole suite in a
  monorepo). Documented in `SECURITY.md`; covered by new tests.
- **One-command, cross-platform installer** (`install.py`) for Windows, macOS, and
  Linux. `install.sh` / `install.ps1` are thin wrappers that exec it.
- PowerShell launcher (`shell/fable.ps1`) alongside the zsh one.
- `uninstall.py` (+ `.sh` / `.ps1` wrappers) — surgical reversal of the install:
  removes bundled files, strips the launcher line, drops only the Fable hooks from
  `settings.json`; leaves user skills, unrelated hooks, and `~/.claude` intact.
- pytest suite for both hooks and the installer; GitHub Actions CI across
  ubuntu/macos/windows × Python 3.9 and 3.12.
- `.gitattributes` (LF for shell/Python, CRLF for PowerShell), `.editorconfig`,
  `SECURITY.md`, `CONTRIBUTING.md`, and this changelog.

### Changed
- The `fable` launcher now defaults to `--effort xhigh` instead of
  `--settings '{"ultracode": true}'`. xhigh still trips the playbook trigger and
  drives heavy reasoning, without ultracode's token-hungry multi-agent
  auto-orchestration; ultracode is now an explicit opt-in (documented in the
  launcher and README).
- `merge_settings.py` writes the absolute interpreter (`sys.executable`) and
  absolute hook paths into `settings.json`, so the hooks fire without `$HOME` or
  `python3` resolution at hook-run time.
- Unified the project owner to **HalalifyMusic** in `LICENSE` and `README`.
- Removed a dead `CONNECTORS.md` link in the `explore-data` skill.

## [0.1.0]

### Added
- Initial fable-mode bundle: the Fable 5 system prompt (`fable-system.md`), the
  `FABLE_PLAYBOOK.md` execution playbook, the `fable-trigger` / `test-after-edit`
  hooks, the `/ground` skill and `grounding-verifier` agent, bundled
  design/testing/MCP skills, and the `fable` zsh launcher.
