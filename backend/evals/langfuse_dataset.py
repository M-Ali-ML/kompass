"""Mirror the golden eval suite into Langfuse as a dataset + dataset runs.

Why this exists (roadmap item 3.5): the pydantic-evals report + local dashboard
already answer "did this run pass?", but they don't give a *longitudinal* view
of a single case's score across many runs / prompt versions. Langfuse dataset
runs do: each `evals.run` invocation becomes one dataset run, every case an
item-run linked to its agent trace, and every assertion a score — so the
Langfuse UI can chart per-case / per-category score history and diff two runs
side by side.

Design (keep pydantic-evals as the source of truth, mirror after the fact):

* `sync_cases()` upserts the golden cases as Langfuse dataset items (stable,
  deduped ids) so runs always target the same items.
* The task (see `evals/tasks.py`) wraps each case in a Langfuse span, then calls
  `create_run_item()` + `experiment_context()` so the agent's own trace becomes
  a first-class *experiment item* — a dataset-run-item linked to the trace, the
  `sdk-experiment` environment, and the `langfuse.experiment.*` span attributes
  that the SDK's own `run_experiment()` sets. Without those attributes a run is
  API-visible but stays invisible in the dataset's **Experiments** tab. The task
  also stamps the trace id onto the `ReportCase` (`set_eval_attribute`) and into
  `_TRACE_IDS`, so `publish_report()` can find the right trace per row (even for
  *failed* cases, which lose their attributes).
* `publish_report()` walks the finished report and attaches scores: one BOOLEAN
  score per assertion on each case's trace, then per-category and overall
  NUMERIC scores on the run itself.

Everything degrades to a no-op when Langfuse isn't configured — the caller
guards on `telemetry.get_langfuse_client()`.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.config import settings
from app.telemetry import get_langfuse_client

from evals.schema import CaseMeta

logger = logging.getLogger("kompass.evals.langfuse")

# The Langfuse dataset name mirrors the pydantic-evals dataset name so the two
# views line up.
DATASET_NAME = "kompass-golden"

# Langfuse tags an experiment run's traces with this reserved environment; the
# dataset's Experiments tab filters on it, so plain dataset-run links (in any
# other environment) never surface there. Mirrors
# langfuse._client.constants.LANGFUSE_SDK_EXPERIMENT_ENVIRONMENT.
_EXPERIMENT_ENVIRONMENT = "sdk-experiment"

# Cached dataset id (needed as an experiment span attribute); resolved once.
_DATASET_ID: str | None = None

# case_name -> trace ids captured during the run (in execution order). Used as
# the fallback link for failed cases, whose ReportCaseFailure carries no
# attributes. Cleared at the start of each run.
_TRACE_IDS: dict[str, list[str]] = defaultdict(list)


def reset_trace_registry() -> None:
    """Clear the per-run trace-id registry (call before evaluate())."""
    _TRACE_IDS.clear()


def register_trace_id(case_name: str, trace_id: str) -> None:
    """Record a case's Langfuse trace id (called from the eval task)."""
    if case_name and trace_id:
        _TRACE_IDS[case_name].append(trace_id)


def _item_id(case_name: str) -> str:
    """Stable, globally-unique dataset-item id (ids can't be reused across
    datasets, so namespace by dataset name)."""
    return f"{DATASET_NAME}::{case_name}"


def _dataset_id(client: Any) -> str | None:
    """Resolve (and cache) the Langfuse dataset id — an experiment span attr."""
    global _DATASET_ID
    if _DATASET_ID is None:
        try:
            _DATASET_ID = client.get_dataset(DATASET_NAME).id
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not resolve Langfuse dataset id: %s", e)
    return _DATASET_ID


async def create_run_item(client: Any, span: Any, *, run_id: str, case_name: str, metadata: dict[str, Any]) -> str | None:
    """Link this case's trace to the dataset run and return the run id.

    Called from the eval task while the case's Langfuse span is open. Uses the
    sync API off the event loop (the SDK does the same) so concurrent cases
    don't block each other. The returned dataset-run id is the experiment id.
    Never raises — telemetry must not fail a run.
    """
    try:
        item = await asyncio.to_thread(
            client.api.dataset_run_items.create,
            run_name=run_id,
            dataset_item_id=_item_id(case_name),
            trace_id=span.trace_id,
            observation_id=span.id,
            metadata=metadata,
        )
        return item.dataset_run_id
    except Exception as e:  # noqa: BLE001
        logger.warning("Langfuse run-item create failed for %s: %s", case_name, e)
        return None


@contextmanager
def experiment_context(client: Any, span: Any, *, dataset_run_id: str, run_id: str, case_name: str) -> Iterator[None]:
    """Mark the open case trace as a Langfuse *experiment item* for its scope.

    Replicates what the SDK's `run_experiment()` does to make a trace show up in
    the dataset's Experiments tab: flip the root span to the `sdk-experiment`
    environment and propagate the experiment identity (id/name/dataset/item) to
    the agent's child spans. Reuses the SDK's own propagation helper; degrades to
    a plain pass-through if those internals aren't importable (e.g. SDK bump).
    """
    try:
        from langfuse._client.attributes import LangfuseOtelSpanAttributes
        from langfuse._client.propagation import (
            PropagatedExperimentAttributes,
            _propagate_attributes,
        )
        from opentelemetry import trace as otel_trace
    except Exception as e:  # noqa: BLE001
        logger.warning("Langfuse experiment internals unavailable (%s); run item only.", e)
        yield
        return

    otel_trace.get_current_span().set_attribute(
        LangfuseOtelSpanAttributes.ENVIRONMENT, _EXPERIMENT_ENVIRONMENT
    )
    with _propagate_attributes(
        experiment=PropagatedExperimentAttributes(
            experiment_id=dataset_run_id,
            experiment_name=run_id,
            experiment_metadata=None,
            experiment_dataset_id=_dataset_id(client),
            experiment_item_id=_item_id(case_name),
            experiment_item_metadata=None,
            experiment_item_root_observation_id=span.id,
        )
    ):
        yield


def sync_cases(cases: list[Any]) -> bool:
    """Ensure the Langfuse dataset exists and upsert every golden case as an item.

    Idempotent: the dataset is keyed by name and items by a stable id, so
    re-running just updates in place. Returns True on success, False if
    Langfuse is unavailable or the sync errored (never raises).
    """
    client = get_langfuse_client()
    if client is None:
        return False

    try:
        client.create_dataset(
            name=DATASET_NAME,
            description="Kompass agent golden eval cases (synced from backend/evals/cases.py).",
        )
        for case in cases:
            meta = case.metadata
            meta_dump = meta.model_dump(mode="json") if isinstance(meta, CaseMeta) else {}
            client.create_dataset_item(
                dataset_name=DATASET_NAME,
                id=_item_id(case.name),
                input=case.inputs.model_dump(mode="json", exclude={"case_name", "case_category"}),
                metadata={"category": meta_dump.get("category"), **meta_dump},
            )
        logger.info("Synced %d cases to Langfuse dataset %r.", len(cases), DATASET_NAME)
        return True
    except Exception as e:  # noqa: BLE001 - telemetry must never break a run
        logger.warning("Langfuse dataset sync failed (continuing): %s", e)
        return False


def _assertion_value(result: Any) -> bool | None:
    val = getattr(result, "value", result)
    return val if isinstance(val, bool) else None


def _base_name(case: Any) -> str:
    return getattr(case, "source_case_name", None) or case.name


def _trace_id_for(case: Any, consumed: set[str]) -> str | None:
    """Resolve a case's Langfuse trace id.

    Successful cases carry it in `attributes` (stamped by the task) — exact.
    Failures lose their attributes, so fall back to the per-run registry,
    skipping trace ids already consumed by a successful sibling repeat.
    """
    attrs = getattr(case, "attributes", None) or {}
    tid = attrs.get("langfuse_trace_id")
    if tid:
        consumed.add(tid)
        return tid
    for candidate in _TRACE_IDS.get(_base_name(case), []):
        if candidate not in consumed:
            consumed.add(candidate)
            return candidate
    return None


def publish_report(
    report: Any,
    agg: dict[str, Any],
    *,
    run_id: str,
) -> str | None:
    """Attach scores to a finished run's experiment items and return its URL.

    The run and its per-case items are already created during the task (see
    `create_run_item` / `experiment_context`); here we walk the report and add
    the scores that turn those items into an evaluation: a BOOLEAN score per
    assertion on each case's trace, plus per-category and overall NUMERIC scores
    on the run. Returns a URL to the dataset (for the console) or None if
    Langfuse is unavailable. Never raises — telemetry must not fail a run.
    """
    client = get_langfuse_client()
    if client is None:
        return None

    consumed: set[str] = set()
    dataset_run_id: str | None = None
    project_id: str | None = None
    dataset_id: str | None = None

    try:
        # The run id (== experiment id) is assigned server-side when the task
        # created the first run item; look it up to hang run-level scores off it.
        try:
            dataset_run_id = client.get_dataset_run(dataset_name=DATASET_NAME, run_name=run_id).id
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not resolve Langfuse dataset run %r: %s", run_id, e)

        for case in _iter_cases(report):
            trace_id = _trace_id_for(case, consumed)
            if not trace_id:
                continue
            for name, result in (getattr(case, "assertions", {}) or {}).items():
                value = _assertion_value(result)
                if value is None:
                    continue
                client.create_score(
                    trace_id=trace_id,
                    name=name,
                    value=1.0 if value else 0.0,
                    data_type="BOOLEAN",
                    comment=getattr(result, "reason", None),
                    environment=_EXPERIMENT_ENVIRONMENT,
                )
            for name, result in (getattr(case, "scores", {}) or {}).items():
                val = getattr(result, "value", None)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    client.create_score(
                        trace_id=trace_id,
                        name=name,
                        value=float(val),
                        data_type="NUMERIC",
                        comment=getattr(result, "reason", None),
                        environment=_EXPERIMENT_ENVIRONMENT,
                    )

        # Failures (task raised → no assertions) still get their trace flagged;
        # the run item itself was already created by the task before the agent
        # ran, so here we only need the error score.
        for failure in getattr(report, "failures", []) or []:
            trace_id = _trace_id_for(failure, consumed)
            if trace_id:
                client.create_score(
                    trace_id=trace_id,
                    name="task_error",
                    value=1.0,
                    data_type="BOOLEAN",
                    comment=getattr(failure, "error_message", None),
                    environment=_EXPERIMENT_ENVIRONMENT,
                )

        # Run-level aggregates so the run's headline numbers are the same ones
        # the CLI/dashboard report — chartable across runs in Langfuse.
        if dataset_run_id:
            for cat, r in agg.get("by_category", {}).items():
                if r.get("pass_rate") is not None:
                    client.create_score(
                        dataset_run_id=dataset_run_id,
                        name=f"category:{cat}",
                        value=float(r["pass_rate"]),
                        data_type="NUMERIC",
                        comment=f"{r['passed']}/{r['total']} assertions",
                        environment=_EXPERIMENT_ENVIRONMENT,
                    )
            overall = _overall_rate(agg)
            if overall is not None:
                client.create_score(
                    dataset_run_id=dataset_run_id,
                    name="overall_pass_rate",
                    value=overall,
                    data_type="NUMERIC",
                    environment=_EXPERIMENT_ENVIRONMENT,
                )

        client.flush()
        try:
            ds = client.get_dataset(DATASET_NAME)
            project_id, dataset_id = ds.project_id, ds.id
        except Exception:  # noqa: BLE001
            pass
    except Exception as e:  # noqa: BLE001
        logger.warning("Langfuse dataset-run publish failed (continuing): %s", e)

    if project_id and dataset_id:
        base = settings.langfuse_base_url.rstrip("/")
        return f"{base}/project/{project_id}/datasets/{dataset_id}"
    return None


def _iter_cases(report: Any) -> list[Any]:
    cases = getattr(report, "cases", None)
    return list(cases) if isinstance(cases, (list, tuple)) else []


def _overall_rate(agg: dict[str, Any]) -> float | None:
    passed = total = 0
    for r in agg.get("by_category", {}).values():
        passed += r.get("passed", 0)
        total += r.get("total", 0)
    return round(passed / total, 4) if total else None
