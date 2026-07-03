# Fable mode launcher. install.py copies this file to ~/.claude/shell/fable.zsh
# and sources it from your shell rc, so the cloned repo can be moved or deleted
# after install. Manual use: `source ~/.claude/shell/fable.zsh`
#
# `fable`          Claude Code pinned to Opus 4.8, Fable Claude-Code behavior
#                  layer appended, xhigh effort, FABLE_MODE=1 declared so
#                  fable-trigger.py injects the playbook at SessionStart.
# `fable --ultra`  Same, plus ultracode: the harness auto-runs multi-agent
#                  workflows for substantive tasks (heavy on tokens).
# `fable doctor`   Verify the whole install/activation chain mechanically.
fable() {
  if [[ "$1" == "doctor" ]]; then
    shift
    python3 "$HOME/.claude/hooks/fable-doctor.py" "$@"
    return
  fi
  local -a extra
  if [[ "$1" == "--ultra" || "$1" == "-u" ]]; then
    shift
    # A file path, not inline JSON: PowerShell 5.1 strips embedded quotes from
    # native-command args, and inline JSON breaks the same way if copy-pasted
    # across shells (issue #2). A path survives quoting everywhere.
    extra=(--settings "$HOME/.claude/ultracode.settings.json")
  fi
  FABLE_MODE=1 claude --model claude-opus-4-8 \
    --append-system-prompt-file "$HOME/.claude/fable-code.md" \
    --effort xhigh "${extra[@]}" "$@"
}
