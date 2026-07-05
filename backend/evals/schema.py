"""Typed schema for the eval suite: case inputs, expected-behavior metadata,
and the serializable trace the evaluators score.

`RunTrace` is intentionally a compact, JSON-serializable projection of the
harness's `EvalRunResult` — it holds exactly what the deterministic evaluators
need (tool names, executed data-service call args, the scenarios payload) so
pydantic-evals can serialize outputs into its report and OTel spans without
choking on live agent objects (RunUsage, ModelMessage, ...).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from evals.harness import EvalRunResult


class Category(str, Enum):
    """Diagnostic buckets so pass rates are actionable, not a single number."""

    TOOL_SELECTION = "tool_selection"
    CONSTRAINT_ADHERENCE = "constraint_adherence"
    ANTI_FABRICATION = "anti_fabrication"
    MANUAL_OVERRIDE = "manual_override"
    PARTY_PROPAGATION = "party_propagation"
    ITINERARY_QUALITY = "itinerary_quality"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"


class CaseInputs(BaseModel):
    """What the task function needs to run one agent turn headless."""

    prompt: str
    # Seed preferences (stands in for the saved global profile), e.g.
    # {"direct_flights_only": true, "currency": "EUR"}.
    preferences: dict[str, Any] | None = None
    # Scripted reply for the ask_clarifying_question HITL stub, if the model
    # asks despite a fully-specified prompt.
    clarifying_answer: str | None = None
    # Follow-up turns for multi-turn refinement cases. Each is sent in order
    # AFTER `prompt`, threading the prior turns' message_history through the
    # same agent + fakes; evaluators score the FINAL turn's trace.
    followups: list[str] = Field(default_factory=list)

    # Auto-populated by build_dataset() from the Case's own `name`/`metadata.
    # category` — pydantic-evals' task callable only receives `CaseInputs`, not
    # the surrounding `Case`, so this is how the eval Langfuse tracing
    # (evals/tasks.py) recovers "which case is this?" to tag/name the trace.
    # Not meant to be set by hand in cases.py.
    case_name: str = ""
    case_category: str = ""


class CaseMeta(BaseModel):
    """Expected-behavior contract for a case. Every field is optional; an
    evaluator emits an assertion ONLY when the relevant field is set, so each
    case is scored solely on the behaviors it actually targets."""

    category: Category
    notes: str = ""

    # --- Tool selection -----------------------------------------------------
    required_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    # e.g. a round trip needs >= 2 one-way search_flights calls.
    min_flight_searches: int | None = None

    # --- Constraint adherence ----------------------------------------------
    # Every scenario's grand_total must be <= this (traveler's currency).
    budget_cap: float | None = None
    # Budget is deliberately infeasible: the agent must NOT emit an over-budget
    # plan (either no scenarios, or every scenario within the cap) — used with
    # `budget_cap` to reward honest refusal instead of a fabricated fit.
    budget_infeasible: bool = False
    # Every search_flights call must pass max_stops == 0.
    direct_only: bool = False
    # Flight legs must depart in daytime hours (no red-eye / overnight).
    no_redeye: bool = False
    # passengers (flights) and guests (lodging) must equal this.
    party_size: int | None = None
    # ISO currency code every scenario payload + flight search must use.
    expect_currency: str | None = None
    # Every produced scenario must carry this traveler count (payload-level;
    # survives multi-turn party-size changes where earlier searches differ).
    expect_travelers: int | None = None

    # --- Human-in-the-loop --------------------------------------------------
    # Required trip info is missing → the agent MUST ask_clarifying_question.
    expect_clarification: bool = False
    # The prompt is complete → the agent must NOT ask_clarifying_question.
    forbid_clarification: bool = False

    # --- Anti-fabrication ---------------------------------------------------
    # Live data is empty → agent must fall back to search_web and flag prices
    # as estimated rather than inventing them.
    expect_estimated: bool = False

    # --- Manual override ----------------------------------------------------
    # Traveler already arranged transport → transportation subtotal must be 0.
    transportation_zero: bool = False

    # --- Itinerary quality (island hopping / detailed plans) ---------------
    min_scenarios: int | None = None
    # Location/name keywords each expected to appear in the lodging list
    # (e.g. every visited island/city has a hotel).
    expect_islands: list[str] = Field(default_factory=list)
    # Minimum number of non-flight legs (ferries/trains/buses).
    min_ground_legs: int | None = None

    # --- LLM-as-judge (soft criteria a Python assert can't capture) --------
    # Judge the final reply is a concise recommendation (picks/justifies an
    # option, next step), not a prose restatement of the day-by-day plan.
    judge_recommendation: bool = False
    # When set, judge that the day-by-day activities match this vibe
    # (e.g. "relaxed foodie", "adventure hiking"). Empty = skip.
    judge_vibe: str = ""


class ToolCallTrace(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class RunTrace(BaseModel):
    """Serializable projection of one agent run for scoring."""

    output_text: str
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    # Executed data-service call args (post-validation), captured by the fakes.
    flight_calls: list[dict[str, Any]] = Field(default_factory=list)
    accommodation_calls: list[dict[str, Any]] = Field(default_factory=list)
    research_calls: list[str] = Field(default_factory=list)
    scenarios_payload: dict[str, Any] | None = None
    usage: dict[str, Any] = Field(default_factory=dict)

    # --- Convenience accessors used by evaluators --------------------------
    @property
    def tool_names(self) -> list[str]:
        return [c.name for c in self.tool_calls]

    @property
    def scenarios(self) -> list[dict[str, Any]]:
        if not self.scenarios_payload:
            return []
        return self.scenarios_payload.get("scenarios", [])

    @property
    def flight_search_calls(self) -> list[dict[str, Any]]:
        return [c for c in self.flight_calls if c.get("method") == "search_flights"]

    @classmethod
    def from_result(cls, res: "EvalRunResult") -> "RunTrace":
        u = res.usage
        return cls(
            output_text=res.output,
            tool_calls=[ToolCallTrace(name=c.name, args=c.args) for c in res.tool_calls],
            flight_calls=list(res.flight_service.calls),
            accommodation_calls=list(res.accommodation_service.calls),
            research_calls=list(res.research_service.calls),
            scenarios_payload=res.scenarios_payload,
            usage={
                "input_tokens": getattr(u, "input_tokens", None),
                "output_tokens": getattr(u, "output_tokens", None),
                "cache_read_tokens": getattr(u, "cache_read_tokens", None),
                "requests": getattr(u, "requests", None),
                "tool_calls": getattr(u, "tool_calls", None),
            },
        )
