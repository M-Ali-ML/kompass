"""The eval task: turn a `CaseInputs` into a scored `RunTrace`.

This is the `Callable[[CaseInputs], Awaitable[RunTrace]]` that pydantic-evals
invokes per case. The optional model override lets the runner evaluate a
cheaper tier (e.g. gemini-2.5-flash) without touching the production agent."""

from __future__ import annotations

from typing import Any

from app.domain import UserPreferences
from app.telemetry import trace_attributes

from evals.harness import run_case, run_conversation
from evals.schema import CaseInputs, RunTrace


def make_task(model: Any = None, *, run_id: str | None = None):
    """Build the task callable.

    `run_id` (the eval run's timestamp) becomes the Langfuse `session_id` so
    every case in one `evals.run` invocation groups into a single Langfuse
    session — distinct from any real trip's session (a UUID thread id) — while
    each case still gets its own named, tagged trace (see `trace_attributes`
    below). A no-op when Langfuse isn't configured (`telemetry.trace_attributes`
    degrades to a null context).
    """
    repeat_counts: dict[str, int] = {}

    async def run_trace(inputs: CaseInputs) -> RunTrace:
        prefs = UserPreferences(**inputs.preferences) if inputs.preferences else None
        case_name = inputs.case_name or "unnamed_case"
        repeat_counts[case_name] = repeat_counts.get(case_name, 0) + 1

        with trace_attributes(
            environment="eval",
            session_id=run_id,
            trace_name=case_name,
            tags=["kompass-eval", inputs.case_category] if inputs.case_category else ["kompass-eval"],
            metadata={
                "eval_case": case_name,
                "eval_category": inputs.case_category,
                "eval_repeat": repeat_counts[case_name],
                "eval_model": str(model) if model else "default",
            },
        ):
            if inputs.followups:
                result = await run_conversation(
                    [inputs.prompt, *inputs.followups],
                    preferences=prefs,
                    clarifying_answer=inputs.clarifying_answer,
                    model=model,
                )
            else:
                result = await run_case(
                    inputs.prompt,
                    preferences=prefs,
                    clarifying_answer=inputs.clarifying_answer,
                    model=model,
                )
        return RunTrace.from_result(result)

    return run_trace
