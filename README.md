<div align="center">

# fable-mode

**Run Claude Fable 5 on Opus 4.8.**
The Mythos-class model the U.S. government pulled after three days — brought back as a system prompt.

![Stars](https://img.shields.io/github/stars/HalalifyMusic/fable-mode?style=social) &nbsp;
![License](https://img.shields.io/badge/license-MIT-blue) &nbsp;
![Claude Code](https://img.shields.io/badge/Claude%20Code-Opus%204.8-d97757) &nbsp;
![Fable 5 Lite](https://img.shields.io/badge/Fable%205-Lite-111111)

One clone, one install: the leaked **Claude Fable 5** system prompt + a measured execution playbook + verification hooks + design and agent skills — wired into Claude Code.

<!-- Hero image: add docs/before-after.png (stock Opus 4.8 vs. fable-mode, same prompt) then uncomment:
<img src="docs/before-after.png" alt="Same prompt, same model — stock Opus 4.8 vs. Opus 4.8 in fable-mode" width="100%">
<sub>Same prompt, same model. Left: stock Opus 4.8. Right: Opus 4.8 in fable-mode.</sub>
-->

</div>

---

## Why this exists

Claude Fable 5 shipped on June 9, 2026 as Anthropic's first Mythos-class model — and was suspended on June 12 under a U.S. export-control directive. You can't call the model right now.

But when its system prompt leaked, people noticed: a lot of what made Fable *feel* different — its taste, its directness, its tool-use instincts — lived in the prompt, not only the weights. Run that prompt on Opus 4.8 and the output changes character. The community calls it **Fable 5 Lite**. This is the complete version for Claude Code, plus the part a leaked prompt can't give you — measured discipline and verification, enforced by hooks.

## Quickstart

```sh
git clone https://github.com/HalalifyMusic/fable-mode
cd fable-mode && ./install.sh
source ~/.zshrc
fable        # Opus 4.8 + Fable prompt + ultracode
```

`install.sh` copies everything into `~/.claude`, adds the `fable` launcher, and merges your settings (with a backup). No model switch, no API key — it runs on the Opus 4.8 you already have.

## What's in the bundle

- **`FABLE_PLAYBOOK.md`** — the core. Fable-5 vs Opus-4-8 tool traces turned into rules: reasoning density (70% vs 47%), verify-after-edit, parallelism — plus a voice layer and an evidence-ledger grounding protocol. Original work, not the leaked prompt.
- **`fable-system.md`** — the leaked Fable 5 system prompt (Anthropic's; see note below).
- **Hooks** — `fable-trigger.py` injects the playbook at `xhigh`/`max`/`ultracode`; `test-after-edit.py` runs your project's tests after each edit and reports the result back — the one habit no model keeps on willpower.
- **`/ground` skill + `grounding-verifier` agent** — a self-terminating grounding loop and a cold verifier that assumes every claim is wrong until the live code proves it.
- **Skills** — `claude-design-patterns` (web-UI engineering), `webapp-testing`, `mcp-builder`, `skill-creator`, `explore-data`.
- **`fable()` launcher** — Opus 4.8 + the prompt + `ultracode` effort.

## The honest ceiling

This gives you Fable's *disposition*, not its raw capability. Reasoning depth, vision, long-horizon autonomy, and design intuition are weights-bound — only partly reachable by instruction. What transfers well: voice, formatting, grounding and verification, design patterns, effort configuration. On verification, parallelism, and communication it actually beats Fable, because those are enforced by hooks instead of left to intention.

## About the bundled pieces

- The Fable 5 system prompt (`fable-system.md`) is Anthropic's IP. It is already mirrored across high-star public repos; it's bundled here only so setup is a single step. Not ours to license, removable on request. It's the *consumer* prompt — trim to the `claude_behavior` section to cut dead weight in a terminal.
- `webapp-testing`, `mcp-builder`, `skill-creator` are from [anthropics/skills](https://github.com/anthropics/skills) (Apache-2.0); `explore-data` is from [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) (Apache-2.0).

## Credits

Made by me — compiled from community sources (leaked prompts, public Anthropic skills) and original measurement and tooling work.

## License

MIT on the original code (see `LICENSE`). The bundled Fable system prompt and the Anthropic skills carry their own terms.
