---
name: fable
description: Activate Fable mode - adopt the Fable execution playbook and the Claude Code behavior layer as standing discipline for this session. Use when the user types /fable, says "fable mode", "use fable", "work like fable", or asks for maximum-discipline execution.
---

# Fable mode

Activate the full Fable discipline for the rest of this session:

1. Read `~/.claude/FABLE_PLAYBOOK.md` (execution discipline: reason before
   acting, observe-then-decide, verify every edit, communication floor,
   grounding protocol). If the file is missing, read `FABLE_PLAYBOOK.md` from
   this skill's repository instead.
2. Read `~/.claude/fable-code.md` (the Claude Code behavior layer: final-message
   contract, readable-over-concise, tool discipline, autonomy and honesty
   rules). Same fallback.
3. Adopt both as standing discipline — they govern every subsequent turn of
   this session, not just the next reply.
4. Confirm activation in one line ("Fable mode active — playbook and behavior
   layer loaded."), then continue with the user's task. Do not summarize the
   documents back.

Scale the heavier machinery to the task: the evidence ledger and the
`grounding-verifier` agent are for non-trivial or hard-to-reverse work, not for
typo fixes (the playbook's own calibration rules apply).
