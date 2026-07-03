# Fable mode launcher. Add to ~/.zshrc, or: `source ~/path/to/fable-mode/shell/fable.zsh`
#
# Launches Claude Code pinned to Opus 4.8 with the Fable Claude-Code behavior
# layer appended and xhigh effort, and declares the mode via FABLE_MODE=1 so
# fable-trigger.py injects the execution playbook at SessionStart — reliable on
# every Claude Code version, not only those that expose effort to hooks.
#
# install.py copies fable-code.md into ~/.claude for you.
# Want multi-agent auto-orchestration too? Add: --settings '{"ultracode": true}'
fable() {
  FABLE_MODE=1 claude --model claude-opus-4-8 \
    --append-system-prompt-file "$HOME/.claude/fable-code.md" \
    --effort xhigh "$@"
}
