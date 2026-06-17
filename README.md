# Fable mode

Make Claude Code (Opus 4.8) behave as much like **Claude Fable 5** as possible — without the model weights.

Fable 5 was Anthropic's Mythos-class model; it launched on 2026-06-09 and was suspended on 2026-06-12 under a US export-control directive, so nobody can use the model right now. But a leaked copy of its system prompt showed that a large part of what made Fable *feel* different — its identity, design instincts, tool-use posture, and response style — lives in the instruction layer, not only the weights. The community calls the result "Fable 5 Lite": run the Fable prompt surface on Opus 4.8. This repo is a complete, opinionated version of that for Claude Code, plus the parts the leaked prompt *couldn't* give you (measured execution discipline and verification, wired as hooks).

## What's the honest ceiling

This gets you Fable's **disposition**, not its capability. Reasoning density, vision quality, long-horizon autonomy, and design intuition are weights-bound and only partly reachable by instruction. What transfers well: response voice, anti-slop formatting, grounding/verification discipline, design engineering patterns, and effort configuration. On the back half — running real tests after edits, parallelizing, communicating — this setup actually *beats* Fable, because those are enforced mechanically rather than left to intention.

## What you get

- **`FABLE_PLAYBOOK.md`** — the core. A measured comparison of Fable-5 vs Opus-4-8 tool traces (reasoning density 70% vs 47%, weaker test-after-edit, etc.) turned into concrete ADOPT/REFUSE rules, a voice layer, and a grounding protocol. This is original work, not the leaked prompt.
- **`hooks/fable-trigger.py`** — a UserPromptSubmit hook that injects the playbook when you're at `xhigh`/`max`/`ultracode` effort, or say "use fable".
- **`hooks/test-after-edit.py`** — a PostToolUse hook that runs the project's tests after each edit and reports pass/fail back to the model. Project-aware (npm/pnpm/yarn/bun, pytest/uv, cargo, go, make), debounced, non-blocking, with a kill switch. This is the mechanical fix for the one habit no model keeps on willpower.
- **`skills/ground/`** + **`agents/grounding-verifier.md`** — a self-terminating evidence-ledger grounding loop and a cold, read-only verifier that assumes every claim is wrong until the live code proves it right.
- **`skills/claude-design-patterns/`** — engineering patterns for building polished web UI (React/Babel pinning, the live-edit "Tweaks" protocol, starter components, methodology), to use alongside the `frontend-design` skill.
- **`shell/fable.zsh`** — the launcher: Opus 4.8 + the Fable system prompt + `ultracode`.

## Install

```sh
./install.sh        # copies hooks/skills/agents into ~/.claude, appends the fable() function, merges settings
```

Then `source ~/.zshrc`. Run `fable` to start a session, or set effort to `xhigh`/`ultracode` in any session to load the playbook.

## The Fable system prompt

`fable-system.md` (Anthropic's Claude Fable 5 system prompt) is bundled here so `install.sh` works out of the box. It's a leaked consumer prompt already widely mirrored on public GitHub repos (thousands of stars, no takedowns). It remains Anthropic's IP — not ours to license, and removable on request. Note it's the *consumer* prompt: most of it (memory, artifacts, image search, copyright rules, consumer tool schemas) is dead weight in a terminal, so consider trimming to the `claude_behavior` section.

## Attribution

- The playbook is original, derived from measured tool-trace data.
- The grounding skill and verifier are adapted from a community grounding rig.
- The design patterns are distilled, in our own words, from Anthropic's leaked Claude Design system prompt — paraphrased engineering rules, not a copy. Review before relying on them.
- `fable-system.md` is Anthropic's Claude Fable 5 system prompt, bundled for convenience and already widely mirrored publicly; it is not ours to license.

## License

MIT (our code only — see `LICENSE`). The bundled Fable system prompt is Anthropic's — not covered by our license and not ours to license.
