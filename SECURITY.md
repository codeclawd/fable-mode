# Security Policy

## Supported versions

fable-mode is a small tooling + prompt bundle, not a versioned library. Security
fixes land on the `main` branch — please run the latest `main`.

## What fable-mode runs on your machine

Installing fable-mode wires two hooks into Claude Code that run **on your own
machine**, with your permissions:

- **`fable-trigger.py`** (UserPromptSubmit) — reads `~/.claude/FABLE_PLAYBOOK.md`
  and injects it into the prompt context. It does not execute project code and
  makes no network calls.
- **`test-after-edit.py`** (PostToolUse on Edit/Write/MultiEdit) — **runs your
  project's own test command** (`npm test`, `pytest`, `cargo test`, `go test`,
  `make test`) automatically after a code edit, to report pass/fail. Editing a
  file can therefore trigger execution of that project's test suite.

Neither hook sends anything over the network. They read/write only under
`~/.claude` and the system temp dir (debounce/marker files), and run the detected
test command in the edited project's directory.

Because the test hook runs a project's test command, **only enable fable-mode in
repositories you trust** — the same caution you would apply to running their
tests yourself. The command is derived from repo content (`package.json` scripts,
a `Makefile` `test:` target, or a `.fable-test` file), so a hostile repository
could point it at an arbitrary command; treat it exactly like running that repo's
build yourself.

### Restricting where it runs (the trust gate)

Set `FABLE_TEST_HOOK_ALLOW` to an `os.pathsep`-separated list of directory
prefixes (`:` on Unix, `;` on Windows). When it is set, the hook auto-runs **only**
for projects at or under one of those roots and stays silent everywhere else — so
editing a freshly-cloned, untrusted repo triggers nothing. When it is unset the
default is zero-config (runs in any project), which is why the trust caution above
applies.

### Turning the test hook off

- Set `FABLE_NO_TEST_HOOK=1` to disable it entirely.
- Set `FABLE_TEST_HOOK_ALLOW=<trusted dirs>` to restrict it to roots you trust.
- Tune `FABLE_TEST_HOOK_DEBOUNCE` / `FABLE_TEST_HOOK_TIMEOUT` (seconds).
- Drop a `.fable-test` file in a project root to pin the exact command it runs
  (e.g. a fast, scoped subset instead of the whole suite). Note this file is repo
  content, so it is governed by the same `FABLE_TEST_HOOK_ALLOW` gate.
- Or remove the `PostToolUse` entry from `~/.claude/settings.json` — `uninstall.py`
  does this for you.

## Bundled third-party content

`fable-system.md` is Anthropic's Claude Fable 5 system prompt, included only so
setup is a single step. It is third-party content, not authored or audited here,
and is removable on request. The skills under `skills/` (`webapp-testing`,
`mcp-builder`, `skill-creator`, `explore-data`) are vendored from upstream
Apache-2.0 repos. Treat all of it as untrusted-origin text.

## Reporting a vulnerability

Please report security issues **privately**, not in a public issue:

- Use GitHub's **"Report a vulnerability"** (the repo's *Security → Advisories*
  tab), or
- if private advisories are disabled, open a minimal public issue asking for a
  private contact channel — do not include details there.

Include what you found, how to reproduce it, and the impact. We'll acknowledge the
report and work on a fix; please allow a reasonable window before public
disclosure.
