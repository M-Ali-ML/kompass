"""The eval task: turn a `CaseInputs` into a scored `RunTrace`.

This is the `Callable[[CaseInputs], Awaitable[RunTrace]]` that pydantic-evals
invokes per case. The optional model override lets the runner evaluate a
cheaper tier (e.g. gemini-2.5-flash) without touching the production agent."""

from __future__ import annotations

from typing import Any

from app.domain import UserPreferences

from evals.harness import run_case, run_conversation
from evals.schema import CaseInputs, RunTrace


def make_task(model: Any = None):
    async def run_trace(inputs: CaseInputs) -> RunTrace:
        prefs = UserPreferences(**inputs.preferences) if inputs.preferences else None
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
