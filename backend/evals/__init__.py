"""Kompass agent evaluation suite.

Runs the REAL agent (real Gemini model, real system prompt) against
DETERMINISTIC fake data services, so score changes can only come from
model/prompt behavior — never from live-data drift.

See artifacts/evals_plan.md at the repo root for the phased roadmap.
"""
