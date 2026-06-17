---
name: ground
description: Self-terminating grounding loop for a development step. Turns assertions, assumptions, and inferences into verified knowledge via an evidence-backed ledger; self-resolves code-determinable forks and logs them; escalates only genuine preference forks; spawns an independent verifier; and emits a plain-English review packet at the user's altitude. Invoke before implementing any non-trivial step, or whenever asked to "ground" something.
---

# /ground — executable grounding protocol

Makes the "verify before done" discipline **self-terminating** (a ledger with a termination
test), **self-resolving** (a decision policy for forks), and **independently verified** (a cold
second agent), so it runs to completion without you re-prompting "ground further" each step.

## Core invariant

Do not return to the user while any load-bearing claim is UNVERIFIED or any code-determinable fork
is unresolved. "Looks done" is not a termination criterion — an empty UNVERIFIED column is.

## 1. Build the ledger

List every claim the step rests on, as a table: `| # | Claim | Status | Evidence |`

- A row is **VERIFIED only** when Evidence is a concrete `file:line` (read) or a command **+ its
  output** (run).
- "Structurally certain" / "by reading" / "likely" / "should" → **UNVERIFIED**. No exceptions.
- **Behavioral claims** — control flow, ordering, teardown, exception propagation, state
  mutation, concurrency — require **run** evidence, not read evidence. Reason only to design the
  check; then run it.
- For any library / framework / API claim, ground truth is the installed version or the official
  docs (Context7) — not memory.
- A claim too vague to mark either way is **split** into checkable sub-claims.

## 2. The five moves

1. Read breadth-first — topology: imports, calls, where state lives (Grep/Glob/Read; fan out
   parallel searches for fan-out questions).
2. Read the private internals — closures, captured vars, callbacks, indirection — not just exports.
3. Test each plan claim against the code — grep the counts, check the visibility.
4. Name what is intentionally excluded, and why.
5. Write findings into the plan / ledger.

## 3. The loop + termination

Run the moves, fill the ledger, repeat. Each pass must verify ≥1 row or split a vague claim.
**Terminate** when a full pass yields no new verifications AND the UNVERIFIED column is empty for
all load-bearing claims.

## 4. Decision policy — make forks resolve themselves

For each fork the grounding surfaces, classify:

- **Code-determinable** — one branch is correct given how the code wires, a project invariant, or
  the development trajectory. → **Decide it.** Write *decision + grounded reasoning + rejected
  alternative(s)* into a decision log. Do not ask.
- **Preference / value** — needs the user's priorities, risk tolerance, or product direction; or
  is irreversible *and* expensive. → **Stop and surface it** inline (markdown list, never
  AskUserQuestion) with a grounded recommendation.
- **Unsure which class** → treat as preference and surface. Conservative on purpose.

The bar: ask only what the code genuinely cannot answer.

## 5. Independent verification

When the ledger is clean, spawn the **grounding-verifier** agent (cold, read-only). Give it the
step goal + the ledger + the diff (if any) — **not** your justification narrative. It performs:

- **(a) Row-check** — each cited evidence actually supports its claim; re-run behavioral checks
  (the run is ground truth regardless of reader).
- **(b) Gap-scan** — independently hunt load-bearing claims the ledger omits: bypass paths,
  untested assumptions, unnamed exclusions, count claims that are off.
- **(c) Summary-fidelity** — confirm the §6 packet faithfully describes the diff.

Resolve every REFUTED / INSUFFICIENT finding (re-ground, fix, or escalate) **before** surfacing.
The verifier reduces but does not eliminate error — it breaks the self-grading loop. Independence
comes from cold context + adversarial stance, not model diversity (same model is fine). For code
changes you may also run the bundled `/code-review` and `/verify` skills alongside it.

## 6. The review packet — abstraction parity

The ledger is an audit trail, not a review surface. Produce a **separate** packet at **the
altitude of the user's original request**, descending to code only in an appendix:

1. **The ask** — restated in the user's words.
2. **What I did** — plain English, same altitude.
3. **Decisions + why + rejected alternatives** — one line each, plain English.
4. **Genuine forks** for the user, if any.
5. **One-command behavioral proof** — before/after, a single command the user can run.
6. *Appendix* — ledger, decision log, full diff. There for drill-down, never required to review.

## 7. Ceiling (autonomy)

Default **ceiling 2**: ground → decide code-determinable forks → implement → verify → **stage
everything and stop before commit** for sign-off. Ceiling 1: also commit autonomously. Ceiling 3:
widen the preference class, escalate more.

## Anti-patterns (hard stops)

- Marking a behavioral claim VERIFIED from reading. Run it.
- Bouncing a code-determinable fork to the user because asking is cheap.
- Treating the ledger as the review surface (forces the user to learn the codebase to review).
- Reactively patching when a check fails — read the code and reason first.
- Surfacing before the verifier has cleared its findings.
