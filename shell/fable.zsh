# Fable mode launcher. Add to ~/.zshrc, or: `source ~/path/to/fable-mode/shell/fable.zsh`
#
# Launches Claude Code (Opus 4.8) with the Fable 5 system prompt appended and
# ultracode effort (sends xhigh to the model AND auto-orchestrates multi-agent
# workflows for substantive tasks — the heaviest mode). ultracode is session-only,
# so it's set via --settings, not --effort. It also trips fable-trigger.py, which
# layers FABLE_PLAYBOOK execution discipline on top.
#
# install.sh copies fable-system.md into ~/.claude for you.
# If ultracode's auto-workflows burn too many tokens, swap --settings for --effort xhigh.
fable() {
  claude --append-system-prompt-file "$HOME/.claude/fable-system.md" --settings '{"ultracode": true}' "$@"
}
