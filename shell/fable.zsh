# Fable mode launcher. Add to ~/.zshrc, or: `source ~/path/to/fable-mode/shell/fable.zsh`
#
# Launches Claude Code (Opus 4.8) with FABLE_CODE.md — the native distillation
# of Fable 5's Claude Code operating rules — appended to the system prompt, and
# ultracode effort (sends xhigh to the model AND auto-orchestrates multi-agent
# workflows for substantive tasks — the heaviest mode). ultracode is session-only,
# so it's set via --settings, not --effort.
#
# NOT the leaked consumer prompt: that file (reference/fable-system-consumer.md)
# is claude.ai-specific and actively conflicts with the Claude Code harness
# (artifact rules, /mnt paths, search etiquette). The distillation is what
# actually transfers.
#
# FABLE_CODE_APPENDED=1 tells fable-trigger.py the disposition layer is already
# in the system prompt, so it only adds the FABLE_PLAYBOOK directive on top.
# If ultracode's auto-workflows burn too many tokens, swap --settings for --effort xhigh.
fable() {
  FABLE_CODE_APPENDED=1 claude --append-system-prompt-file "$HOME/.claude/FABLE_CODE.md" --settings '{"ultracode": true}' "$@"
}
