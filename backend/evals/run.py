"""Run the Kompass golden dataset and report per-category pass rates.

    cd backend && uv run python -m evals.run                 # full dataset, prod model
    uv run python -m evals.run --model google:gemini-2.5-flash
    uv run python -m evals.run --case greek_island_hop_single_plan
    uv run python -m evals.run --repeat 3                     # variance study
    uv run python -m evals.run --concurrency 4

Writes a JSON summary to artifacts/eval_report_<timestamp>.json and prints the
pydantic-evals table plus a per-category assertion pass-rate breakdown.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_evals import Dataset

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


def _aggregate(report: Any) -> dict[str, Any]:
    """Per-category and per-assertion pass rates across all report cases."""
    by_category: dict[str, list[bool]] = defaultdict(list)
    by_assertion: dict[str, list[bool]] = defaultdict(list)
    per_case: list[dict[str, Any]] = []

    for case in _iter_report_cases(report):
        meta = case.metadata
        category = meta.category.value if isinstance(meta, CaseMeta) else str(getattr(meta, "category", "unknown"))
        assertions = getattr(case, "assertions", {}) or {}
        case_results: dict[str, bool] = {}
        for name, result in assertions.items():
            value = _assertion_value(result)
            if value is None:
                continue
            case_results[name] = value
            by_category[category].append(value)
            by_assertion[name].append(value)
        per_case.append(
            {
                "name": case.name,
                "category": category,
                "passed": sum(case_results.values()),
                "total": len(case_results),
                "assertions": case_results,
            }
        )

    def rate(values: list[bool]) -> dict[str, Any]:
        total = len(values)
        passed = sum(values)
        return {"passed": passed, "total": total, "pass_rate": round(passed / total, 3) if total else None}

    return {
        "by_category": {k: rate(v) for k, v in sorted(by_category.items())},
        "by_assertion": {k: rate(v) for k, v in sorted(by_assertion.items())},
        "per_case": per_case,
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
    flagged = [c for c in agg["per_case"] if c["total"] and c["passed"] < c["total"]]
    if not flagged:
        print("  (none — every applicable assertion passed)")
    for c in flagged:
        failed = [k for k, v in c["assertions"].items() if not v]
        print(f"  {c['name']} [{c['category']}]  failed: {', '.join(failed)}")


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

    model = args.model or os.getenv("EVAL_MODEL") or None
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
                "model": model or "<agent default>",
                "repeat": args.repeat,
                "summary": agg,
            },
            indent=2,
        )
    )
    print(f"\nWrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Kompass agent eval suite.")
    parser.add_argument("--model", help="Model override (e.g. google:gemini-2.5-flash).")
    parser.add_argument("--case", action="append", help="Run only named case(s); repeatable.")
    parser.add_argument("--repeat", type=int, default=1, help="Runs per case (variance study).")
    parser.add_argument("--concurrency", type=int, default=3, help="Max concurrent cases.")
    args = parser.parse_args()
    asyncio.run(_amain(args))


if __name__ == "__main__":
    main()
