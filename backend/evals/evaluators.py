"""Deterministic evaluators over a `RunTrace`.

Design notes:

* Each evaluator returns a Mapping of named booleans → pydantic-evals records
  each as a pass/fail *assertion*, so per-behavior pass rates fall out of the
  report directly.
* An evaluator emits a key ONLY when the case's `CaseMeta` targets that
  behavior (otherwise it returns {}), so a case is never penalized for a
  behavior it doesn't exercise.
* Checks assert STRUCTURE and CONSTRAINTS, never exact prices/dates/hotels —
  the golden example (a Milos→Paros→Naxos→Athens island hop) defines the
  *shape* of a good plan (a ferry leg per hop, a hotel per island, subtotals
  that equal the line items), which is what we want the model to reliably
  produce without overfitting to one itinerary or to live data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from evals.schema import CaseMeta, RunTrace

EvalCtx = EvaluatorContext[object, RunTrace, CaseMeta]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower())


def _departure_hour(iso_ts: str) -> int | None:
    m = re.search(r"[T ](\d{2}):", iso_ts or "")
    return int(m.group(1)) if m else None


@dataclass
class ToolSelection(Evaluator):
    """Right tools reached for; wrong tools avoided."""

    def evaluate(self, ctx: EvalCtx) -> dict[str, bool]:
        meta, out = ctx.metadata, ctx.output
        names = out.tool_names
        res: dict[str, bool] = {}
        if meta.required_tools:
            res["required_tools_called"] = all(t in names for t in meta.required_tools)
        if meta.forbidden_tools:
            res["forbidden_tools_avoided"] = all(t not in names for t in meta.forbidden_tools)
        if meta.min_flight_searches is not None:
            res["round_trip_searched"] = (
                len(out.flight_search_calls) >= meta.min_flight_searches
            )
        return res


@dataclass
class ConstraintAdherence(Evaluator):
    """Budget, direct-only, no-red-eye, and party-size constraints honored."""

    def evaluate(self, ctx: EvalCtx) -> dict[str, bool]:
        meta, out = ctx.metadata, ctx.output
        scenarios = out.scenarios
        res: dict[str, bool] = {}

        if meta.budget_cap is not None:
            within_cap = all(
                s["cost_breakdown"]["grand_total"] <= meta.budget_cap + 0.01
                for s in scenarios
            )
            if meta.budget_infeasible:
                # Honest refusal (no plan) or a genuinely within-cap plan both
                # pass; only a fabricated over-budget "fit" fails.
                res["no_overbudget_plan"] = (not scenarios) or within_cap
            else:
                res["budget_respected"] = bool(scenarios) and within_cap

        if meta.expect_currency is not None:
            want = meta.expect_currency.upper()
            payload_ccy = (out.scenarios_payload or {}).get("currency")
            fcalls = out.flight_calls
            checks = [bool(scenarios) and str(payload_ccy or "").upper() == want]
            checks += [str(c.get("currency", "")).upper() == want for c in fcalls]
            res["currency_respected"] = all(checks)

        if meta.expect_travelers is not None:
            res["travelers_propagated"] = bool(scenarios) and all(
                s.get("travelers") == meta.expect_travelers for s in scenarios
            )

        if meta.direct_only:
            fcalls = out.flight_search_calls
            res["direct_flights_only"] = bool(fcalls) and all(
                c.get("max_stops") == 0 for c in fcalls
            )

        if meta.no_redeye:
            flight_legs = [
                leg
                for s in scenarios
                for leg in s["itinerary"].get("legs", [])
                if leg.get("mode") == "flight"
            ]
            if flight_legs:
                res["daytime_flights_only"] = all(
                    (h := _departure_hour(leg.get("departure_time", ""))) is not None
                    and 6 <= h <= 21
                    for leg in flight_legs
                )

        if meta.party_size is not None:
            fcalls = out.flight_search_calls
            acalls = out.accommodation_calls
            checks = [bool(fcalls) or bool(acalls)]  # something must have been searched
            checks += [c.get("passengers") == meta.party_size for c in fcalls]
            checks += [c.get("guests") == meta.party_size for c in acalls]
            res["party_size_propagated"] = all(checks)

        return res


@dataclass
class AntiFabrication(Evaluator):
    """When live data is empty, fall back to search and flag prices estimated."""

    def evaluate(self, ctx: EvalCtx) -> dict[str, bool]:
        meta, out = ctx.metadata, ctx.output
        if not meta.expect_estimated:
            return {}
        payload = out.scenarios_payload
        # A grounded fallback is either a general web search or the ground-
        # transport research tool (ferries/trains have no live price feed).
        fell_back = any(
            t in out.tool_names for t in ("search_web", "search_ground_transport")
        )
        return {
            "fell_back_to_search": fell_back,
            "prices_flagged_estimated": bool(payload) and payload.get("estimated") is True,
        }


@dataclass
class ManualOverride(Evaluator):
    """Traveler already arranged transport → its cost is zeroed, not invented."""

    def evaluate(self, ctx: EvalCtx) -> dict[str, bool]:
        meta, out = ctx.metadata, ctx.output
        if not meta.transportation_zero:
            return {}
        scenarios = out.scenarios
        return {
            "transportation_zeroed": bool(scenarios)
            and all(s["cost_breakdown"]["transportation"] == 0 for s in scenarios)
        }


@dataclass
class InternalConsistency(Evaluator):
    """The itemized line items sum to the subtotals.

    `generate_scenarios` re-derives grand_total from the subtotals server-side,
    so grand_total math is not a model signal — but whether the model's own leg
    and accommodation line items ADD UP to the subtotals it reported is a
    genuine, un-normalized data-quality signal (the golden example's subtotals
    are exactly the sum of its ferry/hotel rows)."""

    def evaluate(self, ctx: EvalCtx) -> dict[str, bool]:
        scenarios = ctx.output.scenarios
        if not scenarios:
            return {}

        def ok(s: dict) -> bool:
            it = s["itinerary"]
            cb = s["cost_breakdown"]
            checks: list[bool] = []
            if it.get("legs"):
                leg_sum = sum(leg.get("cost", 0) or 0 for leg in it["legs"])
                tol = max(1.0, 0.05 * cb["transportation"])
                checks.append(abs(leg_sum - cb["transportation"]) <= tol)
            if it.get("accommodations"):
                acc_sum = sum(a.get("cost", 0) or 0 for a in it["accommodations"])
                tol = max(1.0, 0.05 * cb["accommodation"])
                checks.append(abs(acc_sum - cb["accommodation"]) <= tol)
            return all(checks) if checks else True

        return {"itemized_costs_sum_to_subtotals": all(ok(s) for s in scenarios)}


@dataclass
class PlanQuality(Evaluator):
    """A plan was produced, has the requested breadth, and covers every day."""

    def evaluate(self, ctx: EvalCtx) -> dict[str, bool]:
        meta, out = ctx.metadata, ctx.output
        scenarios = out.scenarios
        res: dict[str, bool] = {"produced_a_plan": bool(scenarios)}

        if meta.min_scenarios is not None:
            res["scenario_count_met"] = len(scenarios) >= meta.min_scenarios

        if scenarios:
            def day_ok(s: dict) -> bool:
                start = date.fromisoformat(s["start_date"])
                end = date.fromisoformat(s["end_date"])
                nights_inclusive = (end - start).days + 1
                have = len(s["itinerary"].get("days", []))
                # ±1 tolerance mirrors the generate_scenarios day guard.
                return have >= nights_inclusive - 1

            res["day_plan_covers_trip"] = all(day_ok(s) for s in scenarios)

        return res


@dataclass
class ItineraryStructure(Evaluator):
    """Island-hopping shape: a ground leg per hop and a hotel on each island."""

    def evaluate(self, ctx: EvalCtx) -> dict[str, bool]:
        meta, out = ctx.metadata, ctx.output
        if not (meta.expect_islands or meta.min_ground_legs is not None):
            return {}
        scenarios = out.scenarios
        res: dict[str, bool] = {}

        if not scenarios:
            if meta.min_ground_legs is not None:
                res["ground_legs_present"] = False
            if meta.expect_islands:
                res["each_island_has_lodging"] = False
            return res

        # Score the richest scenario (most transit legs) for structure.
        richest = max(scenarios, key=lambda s: len(s["itinerary"].get("legs", [])))
        legs = richest["itinerary"].get("legs", [])
        accs = richest["itinerary"].get("accommodations", [])

        if meta.min_ground_legs is not None:
            ground = [leg for leg in legs if leg.get("mode") != "flight"]
            res["ground_legs_present"] = len(ground) >= meta.min_ground_legs

        if meta.expect_islands:
            lodging_text = " ".join(
                _norm(a.get("location", "")) + " " + _norm(a.get("name", "")) for a in accs
            )
            res["each_island_has_lodging"] = all(
                _norm(k) in lodging_text for k in meta.expect_islands
            )

        return res


@dataclass
class HITLBehavior(Evaluator):
    """Asks a clarifying question when (and only when) info is genuinely missing."""

    def evaluate(self, ctx: EvalCtx) -> dict[str, bool]:
        meta, out = ctx.metadata, ctx.output
        asked = "ask_clarifying_question" in out.tool_names
        res: dict[str, bool] = {}
        if meta.expect_clarification:
            res["asked_when_underspecified"] = asked
        if meta.forbid_clarification:
            res["did_not_ask_when_complete"] = not asked
        return res


def _day_digest(scenario: dict, limit: int = 6) -> str:
    """Compact day-by-day activity text for the vibe judge (no prices/dates)."""
    days = scenario.get("itinerary", {}).get("days", [])[:limit]
    lines: list[str] = []
    for d in days:
        acts = "; ".join(
            f"{p.get('period', '')}: {p.get('activity', '')}".strip(": ")
            for p in d.get("schedule", [])
        )
        head = d.get("title") or d.get("description", "")
        lines.append(f"Day {d.get('day_number', '?')} — {head}. {acts}".strip())
    return "\n".join(lines)


@dataclass
class ConciseRecommendation(Evaluator):
    """Judge: the final reply is a short recommendation, not a prose itinerary.

    The system prompt's contract is 'the cards ARE the plan' — the chat reply
    should pick/justify an option or give a next step in a few sentences, not
    re-narrate the day-by-day (which lives in the generative-UI cards)."""

    async def evaluate(self, ctx: EvalCtx) -> dict[str, bool]:
        meta, out = ctx.metadata, ctx.output
        if not (meta.judge_recommendation and out.scenarios):
            return {}
        from evals.judge import judge

        criterion = (
            "The reply is a concise recommendation (roughly 1-4 sentences) that "
            "helps the traveler decide — e.g. it recommends or contrasts the "
            "option(s), or suggests a clear next step. It must NOT be a long "
            "prose restatement of the day-by-day itinerary."
        )
        verdict = await judge(criterion, out.output_text)
        return {"concise_recommendation": verdict.passed}


@dataclass
class VibeMatch(Evaluator):
    """Judge: the day-by-day activities match the requested trip vibe."""

    async def evaluate(self, ctx: EvalCtx) -> dict[str, bool]:
        meta, out = ctx.metadata, ctx.output
        if not (meta.judge_vibe and out.scenarios):
            return {}
        from evals.judge import judge

        richest = max(out.scenarios, key=lambda s: len(s["itinerary"].get("days", [])))
        digest = _day_digest(richest)
        if not digest.strip():
            return {"vibe_matches_activities": False}
        criterion = (
            f"The day-by-day activities clearly reflect a '{meta.judge_vibe}' "
            "trip. Most days should feature activities fitting that vibe."
        )
        verdict = await judge(criterion, digest)
        return {"vibe_matches_activities": verdict.passed}


# All evaluators run on every case; each self-selects via CaseMeta.
ALL_EVALUATORS: list[Evaluator] = [
    ToolSelection(),
    ConstraintAdherence(),
    AntiFabrication(),
    ManualOverride(),
    InternalConsistency(),
    PlanQuality(),
    ItineraryStructure(),
    HITLBehavior(),
    ConciseRecommendation(),
    VibeMatch(),
]
