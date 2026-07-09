# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed — v2: native distillation replaces the leaked prompt
- **`FABLE_CODE.md` is the new core.** An original distillation of Fable 5's
  actual Claude Code operating layer (final-message contract, outcome-first
  summaries, act-don't-ask autonomy, report-vs-fix, evidence-before-state-change,
  irreversibility-scaled reasoning, transferable voice rules) — authored against
  the real Claude Code Fable harness, not inferred from traces.
- The leaked consumer prompt moved to `reference/fable-system-consumer.md` and is
  no longer installed or injected anywhere. It's Fable's *claude.ai* prompt:
  ~42k tokens of artifact/search/copyright rules that don't exist in Claude Code
  and partly conflict with its harness.
- The `fable` launchers now append `FABLE_CODE.md` (not the consumer prompt) and
  set `FABLE_CODE_APPENDED=1` so the trigger hook doesn't double-inject.
- `fable-trigger.py` is now two-layer: `FABLE_CODE.md` injected once per session
  always-on; a *read directive* for `FABLE_PLAYBOOK.md` on trigger phrase or
  heavy effort. If loop-harness-system is installed
  (`~/.claude/docs/LOOP-HARNESS.md`), a one-line bridge is added.
- `FABLE_PLAYBOOK.md` corrected against the harness itself: the
  no-step-narration rule overshot (load-bearing findings should surface the
  moment they happen), and the 24%-text measurement is partly harness design
  (interstitial text may not be shown; the final message must carry everything).

- `FABLE_CODE.md` was then audited by a three-lens fresh-context evaluator
  panel (contradiction-hunt, gap-scan, altitude/overfit — the same discipline
  loop-harness-system prescribes) and corrected where findings survived
  adjudication against the live harness: the deliberation hierarchy is now
  irreversibility-of-action (tool ordering demoted to its measured average),
  the phrase-level narration ban dropped, main-loop vs subagent/headless rules
  scoped explicitly, a §10 precedence section hoisted above the injection
  divider, and ten adjudicated gaps added (skills-first, plan-mode carve-out,
  denied-call-means-adjust, automation-needs-config, compaction staleness,
  hook-output-as-authoritative, findings-in-message-not-files, subagent relay
  contract, discover-project-commands, system-reminder etiquette).

### Fixed — v2
- **Playbook injection silently degraded.** Claude Code caps hook
  `additionalContext` at 10,000 characters; `FABLE_PLAYBOOK.md` is ~21k, so the
  old inline injection was truncated to a file-path preview. The trigger now
  never inlines anything over the cap — the always-on layer is sized to fit, and
  the playbook loads via an explicit Read directive.

### Fixed
- `fable-trigger.py` read the playbook from a hardcoded `/Users/ak/...` path, so
  on-demand injection silently failed for everyone but the original author. It now
  resolves `~/.claude/FABLE_PLAYBOOK.md`.
- `test-after-edit.py` was a silent no-op on Windows — the `npm`/`pnpm`/`yarn`/
  `make` shims raised `FileNotFoundError`. It now resolves the runner via
  `shutil.which` and runs through `cmd.exe` on Windows. Also dropped a duplicate
  `.lockb` skip entry.

### Added
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
