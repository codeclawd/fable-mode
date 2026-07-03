# Fable mode launcher. Add to ~/.zshrc, or: `source ~/path/to/fable-mode/shell/fable.zsh`
#
# `fable`          Claude Code pinned to Opus 4.8, Fable Claude-Code behavior
#                  layer appended, xhigh effort, FABLE_MODE=1 declared so
#                  fable-trigger.py injects the playbook at SessionStart.
# `fable --ultra`  Same, plus ultracode: the harness auto-runs multi-agent
#                  workflows for substantive tasks (heavy on tokens).
# `fable doctor`   Verify the whole install/activation chain mechanically.
#
# install.py copies fable-code.md and fable-doctor.py into ~/.claude for you.
fable() {
  if [[ "$1" == "doctor" ]]; then
    shift
    python3 "$HOME/.claude/hooks/fable-doctor.py" "$@"
    return
  fi
  local -a extra
  if [[ "$1" == "--ultra" || "$1" == "-u" ]]; then
    shift
    extra=(--settings '{"ultracode": true}')
  fi
  FABLE_MODE=1 claude --model claude-opus-4-8 \
    --append-system-prompt-file "$HOME/.claude/fable-code.md" \
    --effort xhigh "${extra[@]}" "$@"
}
