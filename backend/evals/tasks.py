"""The eval task: turn a `CaseInputs` into a scored `RunTrace`.

This is the `Callable[[CaseInputs], Awaitable[RunTrace]]` that pydantic-evals
invokes per case. The optional model override lets the runner evaluate a
cheaper tier (e.g. gemini-2.5-flash) without touching the production agent."""

from __future__ import annotations

from typing import Any

from pydantic_evals import set_eval_attribute

from app.domain import UserPreferences
from app.telemetry import get_langfuse_client, trace_attributes

from evals.harness import run_case, run_conversation
from evals.langfuse_dataset import create_run_item, experiment_context, register_trace_id
from evals.schema import CaseInputs, RunTrace


def make_task(
    model: Any = None,
    *,
    run_id: str | None = None,
    publish: bool = False,
    judge_model: str | None = None,
    repeat: int = 1,
):
    """Build the task callable.

    `run_id` (the eval run's timestamp) becomes the Langfuse `session_id` so
    every case in one `evals.run` invocation groups into a single Langfuse
    session — distinct from any real trip's session (a UUID thread id) — while
    each case still gets its own named, tagged trace (see `trace_attributes`
    below). A no-op when Langfuse isn't configured (`telemetry.trace_attributes`
    degrades to a null context).

    When `publish` is set (the run is being mirrored to a Langfuse dataset run),
    each case's trace is additionally turned into a dataset *experiment item* so
    it appears in the dataset's Experiments tab (see `evals.langfuse_dataset`).
    """
    repeat_counts: dict[str, int] = {}
    run_meta = {
        "model": str(model) if model else "default",
        "judge_model": judge_model,
        "eval_repeat": repeat,
    }

    async def _run_agent(inputs: CaseInputs, prefs: UserPreferences | None):
        if inputs.followups:
            return await run_conversation(
                [inputs.prompt, *inputs.followups],
                preferences=prefs,
                clarifying_answer=inputs.clarifying_answer,
                model=model,
            )
        return await run_case(
            inputs.prompt,
            preferences=prefs,
            clarifying_answer=inputs.clarifying_answer,
            model=model,
        )

    async def run_trace(inputs: CaseInputs) -> RunTrace:
        prefs = UserPreferences(**inputs.preferences) if inputs.preferences else None
        case_name = inputs.case_name or "unnamed_case"
        repeat_counts[case_name] = repeat_counts.get(case_name, 0) + 1
        client = get_langfuse_client()

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
            # Wrap the agent run in a Langfuse span so this case gets its own
            # named trace whose id we can (a) stamp onto the pydantic-evals
            # ReportCase for exact per-row score linking and (b) register for
            # failed-case fallback. No-op branch when Langfuse is off.
            if client is not None:
                with client.start_as_current_observation(name=case_name, as_type="span") as span:
                    trace_id = span.trace_id
                    set_eval_attribute("langfuse_trace_id", trace_id)
                    register_trace_id(case_name, trace_id)
                    # Link the trace to the dataset run and mark it as an
                    # experiment item (Experiments-tab visible). Done before the
                    # agent runs so even a raising case still yields an item.
                    dataset_run_id = (
                        await create_run_item(
                            client, span, run_id=run_id, case_name=case_name,
                            metadata={**run_meta, "category": inputs.case_category},
                        )
                        if publish and run_id
                        else None
                    )
                    if dataset_run_id:
                        with experiment_context(
                            client, span, dataset_run_id=dataset_run_id,
                            run_id=run_id, case_name=case_name,
                        ):
                            result = await _run_agent(inputs, prefs)
                    else:
                        result = await _run_agent(inputs, prefs)
                    span.set_trace_io(input=inputs.prompt, output=result.output)
            else:
                result = await _run_agent(inputs, prefs)
        return RunTrace.from_result(result)

    return run_trace
