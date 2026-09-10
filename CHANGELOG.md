# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed — v3: Fable 5.1 audit (2026-09-10)
- **Launcher defaults to Fable 5.1.** `fable` runs `--model ${FABLE_MODEL:-claude-fable-5-1}`
  (`$env:FABLE_MODEL` on PowerShell). Fable 5.1 is GA; the "you can't call the
  model" premise in the README was stale. `FABLE_MODEL=claude-opus-4-8 fable`
  keeps the Opus "Fable 5 Lite" path. Verified live: under `--model
  claude-fable-5-1` the harness reports "You are powered by the model named
  Fable 5.1"; print-mode `modelUsage.canonicalModel` shows `claude-opus-5`,
  which is an accounting alias, not a fallback (the same probe under
  `--model claude-opus-5` reports Opus 5 with a different knowledge cutoff).
- **`FABLE_CODE.md` re-audited by Fable 5.1 against its own Claude Code
  harness.** Added the rules the v2 distillation missed: scope discipline
  (the requested scope is the deliverable; state a concern then keep building;
  finish every unblocked part and say what was left out; a reaffirmed request
  is the user's decision), the precise final-message rules (twenty-word
  sentences, no em-dashes/parentheticals/arrow chains, numbers and code out of
  prose, header and bullet limits, no closing offer), uncertainty-mid-task
  ordering, the pending-subagent fabrication ban, they/them default, and
  plain one-sentence refusals. The injectable half is under 9k chars and contains
  zero em-dashes, so the file follows its own writing rule.
- `/ground`: preference forks use AskUserQuestion in an interactive session
  (the old "never AskUserQuestion" contradicted the harness); headless runs
  write the fork into the report and stop.
- `/fable`, `grounding-verifier`, playbook header: Fable 5.1 host notes; the
  verifier's report contract (final message goes to the caller, no preamble).
- `claude-design-patterns`: Claude Artifacts block unpkg by CSP; use cdnjs.

### Fixed
- **`shell/fable.ps1` was unrunnable on Windows since f3d5524.** A bad CRLF
  conversion left every line ending in the literal two-byte text `\r` before
  the real CRLF, so the backtick line-continuations escaped a backslash instead
  of continuing the line and `claude --model …` ran as orphaned statements.
  Stripped, with a content test that fails on the same shape in any `.ps1`.
- `fable-trigger.py` marker GC never pruned anything: the glob was `fable-*-`
  (names ending in a dash) while markers are `fable-<kind>-<sid>`. Now
  `fable-code-*` + `fable-playbook-*` (this hook's own kinds only, so an
  unrelated week-old `/tmp/fable-notes.txt` is never deleted), with a regression test.
- New test guards the shipped `FABLE_CODE.md` under the hook cap in the real
  worst case (preamble + loop-harness bridge + playbook directive together);
  the directive itself lost its plumbing sentence to make room.

### Added — activation reliability (from @denfry, PR #3, adapted)
- **`fable doctor`** — one command that verifies the whole install/activation
  chain: files present, hooks registered (settings.json + settings.local.json),
  interpreter paths, launcher profile lines, Claude CLI version/flags, a
  live-fire injection test, and transcript evidence of past activations.
- **Dual-event trigger hook.** `fable-trigger.py` now fires on both SessionStart
  and UserPromptSubmit. SessionStart injection works on every Claude Code version
  (not just 2.1.199+) when the launcher declares `FABLE_MODE=1`. Compact re-injects
  into wiped context; clear re-arms the once-per-session guards.
- **`FABLE_MODE=1` from the launcher** — the `fable` command now declares the
  mode so the hook injects at session start without depending on the effort field
  in the hook payload.
- **Auto-activation heuristic.** A task-shaped prompt (task verbs, code fences,
  file paths, multi-step markers, length — bilingual ru/en) auto-loads the
  playbook once per session. Opt out with `FABLE_AUTO=0`.
- **`/fable` skill** — explicit mid-session activation: reads the playbook +
  behavior layer and adopts both, no launcher required.
- **`fable --ultra`** — ultracode auto-orchestration behind a flag, using a
  settings file (fixes PowerShell 5.1 quote-stripping on inline JSON).
- **Test hook trust gate.** `FABLE_TEST_HOOK_ALLOW` restricts auto-execution to
  trusted directory prefixes; `.fable-test` file pins the exact command per
  project. The hook now skips when the edit itself failed, and GCs stale markers.
- **Skill preservation on reinstall.** Bundled skills carry a `.fable-mode-bundled`
  marker; a same-named user skill is backed up instead of overwritten.
- **`test_content.py`** — test guard preventing dead personal references
  (`~/Downloads/...`, measurement scripts) in shipped content.
- **42 pytest tests** (up from 3), covering trigger, doctor, installer,
  uninstaller round-trip, test-after-edit, launchers, and content guards.

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
