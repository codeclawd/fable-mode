# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- The shell profile sourced the launcher from the cloned repo, so deleting or
  moving the clone broke every new shell, and a re-install from a new path
  silently kept the stale line. The installer now copies `fable.ps1`/`fable.zsh`
  into `~/.claude/shell/` and sources the stable copy; a stale launcher line is
  replaced, not kept.
- Auto/effort-activated sessions lost the playbook forever after a compaction:
  SessionStart re-injected only under `FABLE_MODE=1`, while the session marker
  blocked the UserPromptSubmit path. The trigger hook now re-injects on
  `source == "compact"` whenever the marker proves the mode was active, and
  drops the marker on `source == "clear"` so the once-per-session paths re-arm.
- `FABLE_PLAYBOOK.md` instructed the model to read the author's personal files
  (`~/Downloads/Fable_Mindset_public.md`, `~/compare_models.py`,
  `~/fable_dataset_delta.py`, `reference/llm-bias-awareness.md`) that no user
  has — every fable session risked a failing Read. They are now provenance
  notes, not paths; a content-guard test keeps them out.
- The `/fable` skill's fallback ("read the playbook from this skill's
  repository") was unreachable after install — the installed skill is a lone
  SKILL.md. The fallback now points at `fable doctor` / re-running the
  installer.
- The installer silently `rmtree`'d a user's own `~/.claude/skills/<name>`
  when it collided with a bundled skill name; it now preserves such
  directories under `~/.claude/backups/skills/` and marks its own copies with
  a `.fable-mode-bundled` file. The uninstaller removes only marked
  directories.
- `test-after-edit.py` ran the suite even when the Edit tool itself had
  failed (reporting a stale result), and `fable.ps1 doctor` hardcoded
  `python`, breaking on machines where only `py`/`python3` exists. Both
  fixed; the doctor subcommand now falls back across `python`/`py`/`python3`.
- Session/debounce marker files accumulated in `%TEMP%` forever on Windows;
  both hooks now garbage-collect markers older than a week.
- "Invalid JSON provided for --settings" on Windows PowerShell 5.1 (#2): PS 5.1
  strips embedded quotes when building the native command line, so the inline
  `--settings '{"ultracode": true}'` reached claude as `{ultracode: true}`. The
  launchers now pass a settings *file* (`~/.claude/ultracode.settings.json`,
  shipped and installed), which survives quoting on every shell and PS version.
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
- Double-injection guard: before the once-per-session auto/effort injection,
  the trigger hook scans the session transcript for a "Fable mode active"
  line — a session already activated via the `/fable` skill doesn't get a
  second copy of the playbook.
- On Windows the launcher is now installed into the `$PROFILE` of **both**
  PowerShell 7 and Windows PowerShell 5.1 when both are present.
- `fable doctor` now also verifies the launcher line in the shell profiles
  (a line pointing at a missing file is a hard failure), accepts hooks
  registered in `settings.local.json`, probes `claude --help` for the
  `--effort` / `--append-system-prompt-file` flags the launcher relies on,
  and checks the installed `~/.claude/shell/` launcher copies.
- The auto-activation heuristic learned more everyday task verbs
  (update/upgrade/remove/delete/deploy/rename/write; удалить/обновить/
  написать/запустить/перенести/убрать).
- Auto-activation: `fable-trigger.py` scores prompt complexity (ru+en signals:
  task verbs, code fences, file paths, multi-step markers, length) and loads
  the playbook by itself for task-shaped prompts, once per session, in any
  session — no launcher or phrase needed. Opt out with `FABLE_AUTO=0`.
- `fable --ultra` (alias `-u`): launches with ultracode auto-orchestration; new
  "Orchestration" section in the playbook (fan-out, adversarial verification
  via `grounding-verifier`, plan-gating, calibration).
- `fable doctor`: one-command diagnosis of the install/activation chain —
  files, registered hooks, interpreter paths, Claude Code version, a live-fire
  injection test, and transcript evidence of past activations.
- The `/fable` skill triggers proactively at the start of non-trivial tasks.
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
