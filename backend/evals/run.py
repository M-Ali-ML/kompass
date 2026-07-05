"""Run the Kompass golden dataset and report per-category pass rates.

    cd backend && uv run python -m evals.run                 # full dataset, prod model
    uv run python -m evals.run --model google:gemini-2.5-flash
    uv run python -m evals.run --judge-model google:gemini-2.5-flash-lite
    uv run python -m evals.run --case greek_island_hop_single_plan
    uv run python -m evals.run --repeat 3                     # variance study
    uv run python -m evals.run --concurrency 4

Model selection (CLI flag > env var > default):
  * agent-under-test: --model  > EVAL_MODEL       > LLM_MODEL (test what ships)
  * LLM judge:        --judge-model > EVAL_JUDGE_MODEL > gemini-2.5-flash-lite
Env vars can be set in the shell or backend/.env (loaded via app.config.Settings).

Writes a JSON summary to artifacts/eval_report_<timestamp>.json and prints the
pydantic-evals table plus a per-category assertion pass-rate breakdown.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_evals import Dataset

from app.config import settings

from evals.cases import build_dataset
from evals.schema import CaseMeta
from evals.tasks import make_task

_ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"


def _assertion_value(result: Any) -> bool | None:
    """Extract the boolean from a pydantic-evals assertion result."""
    val = getattr(result, "value", result)
    return val if isinstance(val, bool) else None


def _iter_report_cases(report: Any) -> list[Any]:
    if getattr(report, "cases", None):
        return list(report.cases)
    cases: list[Any] = []
    for group in getattr(report, "case_groups", []) or []:
        cases.extend(getattr(group, "cases", []) or [])
    return cases


def _rate(values: list[bool]) -> dict[str, Any]:
    total = len(values)
    passed = sum(values)
    return {"passed": passed, "total": total, "pass_rate": round(passed / total, 3) if total else None}


def _aggregate(report: Any) -> dict[str, Any]:
    """Per-category and per-assertion pass rates across all report runs, plus a
    per-case view that collapses `--repeat` runs and flags flaky cases.

    Category / assertion rates count EVERY run (all repeats) so thresholds are
    estimated from the full sample. `per_case` collapses repeats of the same
    source case into one row: an assertion passes only if it passed on every
    repeat, and the case is `flaky` when any assertion was mixed across repeats
    or a repeat errored out.
    """
    by_category: dict[str, list[bool]] = defaultdict(list)
    by_assertion: dict[str, list[bool]] = defaultdict(list)

    # Group runs by the source case name (identical across --repeat runs).
    grouped: dict[str, dict[str, Any]] = {}
    for case in _iter_report_cases(report):
        meta = case.metadata
        category = meta.category.value if isinstance(meta, CaseMeta) else str(getattr(meta, "category", "unknown"))
        key = getattr(case, "source_case_name", None) or case.name
        group = grouped.setdefault(
            key, {"category": category, "runs": defaultdict(list), "ok_runs": 0, "error_runs": 0}
        )
        group["ok_runs"] += 1
        assertions = getattr(case, "assertions", {}) or {}
        for name, result in assertions.items():
            value = _assertion_value(result)
            if value is None:
                continue
            by_category[category].append(value)
            by_assertion[name].append(value)
            group["runs"][name].append(value)

    # Errored runs (task raised) never produce assertions — count them per case.
    for failure in getattr(report, "failures", []) or []:
        key = getattr(failure, "source_case_name", None) or getattr(failure, "name", "unknown")
        meta = getattr(failure, "metadata", None)
        category = meta.category.value if isinstance(meta, CaseMeta) else str(getattr(meta, "category", "unknown"))
        group = grouped.setdefault(
            key, {"category": category, "runs": defaultdict(list), "ok_runs": 0, "error_runs": 0}
        )
        group["error_runs"] += 1

    per_case: list[dict[str, Any]] = []
    for name, group in grouped.items():
        runs = group["runs"]
        collapsed = {aname: all(vals) for aname, vals in runs.items()}
        assertion_flaky = any(0 < sum(vals) < len(vals) for vals in runs.values())
        flaky = assertion_flaky or group["error_runs"] > 0
        per_case.append(
            {
                "name": name,
                "category": group["category"],
                "passed": sum(collapsed.values()),
                "total": len(collapsed),
                "assertions": collapsed,
                "runs": group["ok_runs"] + group["error_runs"],
                "error_runs": group["error_runs"],
                "flaky": flaky,
                # Per-assertion pass fraction across repeats (only kept when >1).
                "assertion_rates": (
                    {aname: round(sum(v) / len(v), 3) for aname, v in runs.items()}
                    if any(len(v) > 1 for v in runs.values())
                    else {}
                ),
            }
        )
    per_case.sort(key=lambda c: (c["category"], c["name"]))

    return {
        "by_category": {k: _rate(v) for k, v in sorted(by_category.items())},
        "by_assertion": {k: _rate(v) for k, v in sorted(by_assertion.items())},
        "per_case": per_case,
        "flaky_cases": sorted(c["name"] for c in per_case if c["flaky"]),
    }


def _print_summary(agg: dict[str, Any]) -> None:
    print("\n=== Per-category pass rates ===")
    for cat, r in agg["by_category"].items():
        pct = f"{r['pass_rate'] * 100:.0f}%" if r["pass_rate"] is not None else "n/a"
        print(f"  {cat:<24} {r['passed']:>3}/{r['total']:<3}  {pct}")

    print("\n=== Per-assertion pass rates ===")
    for name, r in agg["by_assertion"].items():
        pct = f"{r['pass_rate'] * 100:.0f}%" if r["pass_rate"] is not None else "n/a"
        print(f"  {name:<34} {r['passed']:>3}/{r['total']:<3}  {pct}")

    print("\n=== Cases needing attention ===")
    flagged = [
        c for c in agg["per_case"]
        if (c["total"] and c["passed"] < c["total"]) or c["error_runs"]
    ]
    if not flagged:
        print("  (none — every applicable assertion passed)")
    for c in flagged:
        failed = [k for k, v in c["assertions"].items() if not v]
        err = f" errored {c['error_runs']}/{c['runs']} run(s);" if c["error_runs"] else ""
        detail = f" failed: {', '.join(failed)}" if failed else ""
        print(f"  {c['name']} [{c['category']}] {err}{detail}".rstrip())

    if agg["flaky_cases"]:
        print("\n=== Flaky across repeats (non-deterministic) ===")
        for c in agg["per_case"]:
            if not c["flaky"]:
                continue
            mixed = {k: v for k, v in c["assertion_rates"].items() if 0 < v < 1}
            bits = ", ".join(f"{k}={v:.0%}" for k, v in mixed.items())
            err = f" errored {c['error_runs']}/{c['runs']}" if c["error_runs"] else ""
            print(f"  {c['name']} [{c['category']}]{err}{'  ' + bits if bits else ''}")


async def _amain(args: argparse.Namespace) -> None:
    dataset: Dataset = build_dataset()
    if args.case:
        dataset = Dataset(
            name="kompass-golden-subset",
            cases=[c for c in dataset.cases if c.name in set(args.case)],
            evaluators=list(dataset.evaluators),
        )
        if not dataset.cases:
            raise SystemExit(f"No cases matched: {args.case}")

    model = args.model or settings.eval_model
    if args.judge_model:
        settings.eval_judge_model = args.judge_model
    task = make_task(model)

    report = await dataset.evaluate(
        task,
        max_concurrency=args.concurrency,
        repeat=args.repeat,
        progress=True,
    )

    report.print(include_input=False, include_output=False, include_durations=True)

    agg = _aggregate(report)
    _print_summary(agg)

    _ARTIFACTS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = _ARTIFACTS / f"eval_report_{stamp}.json"
    out_path.write_text(
        json.dumps(
            {
                "timestamp": stamp,
                "model": model or "<agent default (LLM_MODEL)>",
                "judge_model": settings.eval_judge_model,
                "repeat": args.repeat,
                "summary": agg,
            },
            indent=2,
        )
    )
    print(f"\nWrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Kompass agent eval suite.")
    parser.add_argument("--model", help="Agent-under-test model override (else EVAL_MODEL / LLM_MODEL).")
    parser.add_argument("--judge-model", help="LLM-judge model override (else EVAL_JUDGE_MODEL).")
    parser.add_argument("--case", action="append", help="Run only named case(s); repeatable.")
    parser.add_argument("--repeat", type=int, default=1, help="Runs per case (variance study).")
    parser.add_argument("--concurrency", type=int, default=3, help="Max concurrent cases.")
    args = parser.parse_args()
    asyncio.run(_amain(args))


if __name__ == "__main__":
    main()
