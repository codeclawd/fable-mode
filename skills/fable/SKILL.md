---
name: fable
description: Activate Fable mode - adopt the Fable execution playbook and the Claude Code behavior layer as standing discipline for this session. Use when the user types /fable, says "fable mode", "use fable", "work like fable", or asks for maximum-discipline execution - and PROACTIVELY at the start of any non-trivial engineering task (multi-step implementation, refactor, migration, long debugging session) when the playbook is not already in context.
---

# Fable mode

Activate the full Fable discipline for the rest of this session:

1. Read `~/.claude/FABLE_PLAYBOOK.md` (execution discipline: reason before
   acting, observe-then-decide, verify every edit, communication floor,
   grounding protocol).
2. Read `~/.claude/FABLE_CODE.md` (the Claude Code behavior layer: final-message
   contract, readable-over-concise, tool discipline, autonomy and honesty
   rules).
   If either file is missing, the install is broken — don't hunt for other
   copies. Tell the user to run `fable doctor` (or re-run `python install.py`
   from the fable-mode checkout), then continue with the task, applying
   whatever Fable discipline is already in context.
3. Adopt both as standing discipline — they govern every subsequent turn of
   this session, not just the next reply.
4. Confirm activation in one line ("Fable mode active — playbook and behavior
   layer loaded."), then continue with the user's task. Do not summarize the
   documents back.

If the playbook is already in this context (look for a "Fable mode active"
injection from the hook), skip the reads: confirm activation in one line and
apply `FABLE_CODE.md` from context, reading it only if absent.

Scale the heavier machinery to the task: the evidence ledger and the
`grounding-verifier` agent are for non-trivial or hard-to-reverse work, not for
typo fixes (the playbook's own calibration rules apply).
