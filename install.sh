#!/usr/bin/env bash
# Install Fable mode into ~/.claude and ~/.zshrc. Idempotent; backs up settings.json.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE="$HOME/.claude"
mkdir -p "$CLAUDE/hooks" "$CLAUDE/skills" "$CLAUDE/agents"

echo "→ hooks"
cp "$REPO/hooks/fable-trigger.py"   "$CLAUDE/hooks/"
cp "$REPO/hooks/test-after-edit.py" "$CLAUDE/hooks/"

echo "→ playbook"
cp "$REPO/FABLE_PLAYBOOK.md" "$CLAUDE/FABLE_PLAYBOOK.md"

echo "→ fable system prompt"
cp "$REPO/fable-system.md" "$CLAUDE/fable-system.md"

echo "→ skills (all bundled) + agent"
for d in "$REPO"/skills/*/; do cp -R "$d" "$CLAUDE/skills/"; done
cp "$REPO/agents/grounding-verifier.md" "$CLAUDE/agents/"

echo "→ launcher (~/.zshrc)"
if ! grep -q 'fable()' "$HOME/.zshrc" 2>/dev/null; then
  printf '\n# Fable mode (added by fable-mode/install.sh)\nsource "%s/shell/fable.zsh"\n' "$REPO" >> "$HOME/.zshrc"
  echo "  added source line"
else
  echo "  fable() already present — skipped"
fi

echo "→ settings.json (alwaysThinkingEnabled + hooks; backup written)"
python3 - "$CLAUDE/settings.json" <<'PY'
import json, os, sys, shutil
p = sys.argv[1]
d = json.load(open(p)) if os.path.exists(p) else {}
if os.path.exists(p):
    shutil.copy(p, p + ".bak")
d["alwaysThinkingEnabled"] = True
hooks = d.setdefault("hooks", {})
def ensure(event, entry, needle):
    arr = hooks.setdefault(event, [])
    if not any(needle in h.get("command", "") for e in arr for h in e.get("hooks", [])):
        arr.append(entry)
ensure("UserPromptSubmit",
       {"hooks": [{"type": "command", "command": "python3 $HOME/.claude/hooks/fable-trigger.py"}]},
       "fable-trigger.py")
ensure("PostToolUse",
       {"matcher": "Edit|Write|MultiEdit",
        "hooks": [{"type": "command", "command": "python3 $HOME/.claude/hooks/test-after-edit.py"}]},
       "test-after-edit.py")
json.dump(d, open(p, "w"), indent=2)
print("  settings.json updated")
PY

echo
echo "Done. Now:"
echo "  1. source ~/.zshrc"
echo "  2. run: fable"
