---
name: eval-log-updater
description: Update the eval suite's documentation (docs/evals.md technical reference and docs/evals.html chronological learnings log) every time the LLM agent eval suite (backend/evals/) is run. Run this skill immediately after any `uv run python -m evals.run` invocation, whether triggered directly or via a debugging/fix session.
---

# Skill: Keeping the Eval Log Current

## Purpose
The eval suite (`backend/evals/`) is only valuable as a portfolio/engineering artifact if its findings are captured, not just printed to a terminal and forgotten. This skill makes updating `docs/evals.html` a **mandatory, immediate** follow-up to running the suite — not something deferred to "later cleanup" — so the chronological log stays an honest, real-time record of what every run actually found, matching the philosophy already stated in [`docs/evals.md`](../../../docs/evals.md): *"a running, chronological record of what each eval run actually found."*

This skill is a specialization of [post-docs-updater](../post-docs-updater/SKILL.md) focused specifically on eval runs; it fires more eagerly (every run, not just "when something structural changes").

---

## When to Execute this Skill
You **MUST** invoke this skill immediately after:
1. **Any `uv run python -m evals.run` invocation** (full suite, `--case` subset, `--repeat` variance study, or a debugging one-off) that you ran as part of the current task — whether it passed cleanly, surfaced a regression, or errored out.
2. **Any fix applied as a result of an eval finding** (prompt change, evaluator fix, case rewording, agent/tool code change) that you then re-verified with another eval run.
3. **Any structural change to the suite itself** (new evaluator, fixture, case category, CLI flag, schema field, or file under `backend/evals/`) — even without a specific "finding" to log.

Do not batch this up across multiple unrelated sessions — update it the same turn you ran the eval, while the root cause and evidence (numbers, error messages, case names) are fresh and available.

---

## Execution Steps

### 1. Gather the Evidence From the Run
Before writing anything, have on hand:
* The command you ran (exact flags: `--model`, `--judge-model`, `--case`, `--repeat`, `--concurrency`).
* The per-category / per-assertion pass rates and the "cases needing attention" / "flaky across repeats" sections from the console output.
* For each real finding: the case name(s), the failing assertion(s), a short root-cause diagnosis, and — if you fixed it — a before/after number or before/after behavior.
* Distinguish **infra noise** (429/504/503 from the model or judge provider) from **real signal** (a genuine assertion failure or reproducible model behavior) — see `docs/evals.md` §9 for the established pattern. Only log infra noise if it's a new/notable pattern (e.g. a specific case reproducibly 504s); routine rate-limit blips aren't worth a log entry.

### 2. Update `docs/evals.html` (always, for any real finding)
Read the file first, then append a **new entry at the bottom of the timeline**, just before its closing `</div>` (chronological — oldest first, matching the page's own stated ordering) inside the existing timeline structure (`.timeline` / `.t-item`, with `.pill.{phase,done,info,partial,todo}` status badges — check the current markup, don't invent new classes). Each entry needs:
* A date (use the current session date).
* A short, specific headline (e.g. "Group-of-6 'friends' framing causes silent price fabrication").
* What was run (command/scope).
* What was found (numbers, case names, the actual error/assertion).
* Root cause, if diagnosed.
* The fix applied and the re-verification result (e.g. "3/3 repeats clean after the fix"), or "Open" if unresolved.
* Never rewrite or delete prior entries — this is an append-only log. If a previously-"open" issue is later resolved, add a *new* entry that references the old one rather than editing history.

### 3. Update `docs/evals.md` (only for structural/architectural changes)
Only touch the technical reference when the run led to a change in the suite's *shape*: a new evaluator, case category, fixture, CLI flag, schema field, or a revised baseline/threshold number in §9. Keep the file map (§2), evaluator table (§6), and baseline section (§9) honest about actual current file/class names and numbers. Routine re-runs with no structural change don't need `evals.md` edits — that's what `evals.html` is for.

### 4. Cross-check `artifacts/evals_plan.md` (if it exists locally)
This is a git-ignored internal roadmap/checklist, not published docs — but if your run changes a Phase's status (e.g. moves an item from open to fixed, or surfaces a new one), update its checkboxes and status blurb too so the internal plan doesn't drift from the public docs.

### 5. Verify Consistency
* `docs/evals.md` and `docs/evals.html` must not contradict each other (e.g. don't call something "open" in one and "fixed" in the other).
* If numbers changed (pass rates, case count, evaluator count), update every place they're quoted (both doc files, and `README.md`'s eval blurb if the headline numbers there are now stale).

---

## Formatting Guidelines
* Use repo-relative links only (from `docs/`, e.g. `[cases.py](../backend/evals/cases.py)`); never machine-absolute `file:///Users/...` paths.
* Match the existing tone in `evals.html`: concrete, numbers-first, honest about what's still open — not a marketing summary.
* Keep `evals.md` prose-reference style (structural facts) separate from `evals.html`'s log style (dated narrative) — don't turn `evals.md` into a change log.
