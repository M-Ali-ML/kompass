"""Headless eval harness: run one case against the real agent + fake data.

The REAL parts: the Gemini model configured in settings, the production system
prompt (FilePromptService over app/agent/prompts), and the full kompass_agent
tool surface. The FAKE parts: flights, accommodations, and grounded research,
served deterministically from evals/fixtures.py.

Usage (smoke run):

    cd backend && uv run python -m evals.harness "Plan a weekend in Lisbon \
        from Berlin, Sep 18-21 2026, 2 people, under 900 EUR total."
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.toolsets import FunctionToolset
from pydantic_ai.usage import RunUsage, UsageLimits

from app.adapters.file_prompt_service import FilePromptService
from app.agent.agent import kompass_agent
from app.agent.dependency import AgentDependencies
from app.domain import UserPreferences

from evals.fakes import FakeAccommodationService, FakeFlightService, FakeResearchService

_PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "agent", "prompts"
)

# Mirror production dispatch (app/api/routes.py) so eval behavior matches prod.
_USAGE_LIMITS = UsageLimits(request_limit=30)
_MODEL_SETTINGS = {"timeout": 60.0}


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]


@dataclass
class EvalRunResult:
    """Everything evaluators need from one agent run."""

    prompt: str
    output: str
    tool_calls: list[ToolCall]
    tool_returns: dict[str, list[Any]]        # tool name -> ordered return values
    scenarios_payload: dict[str, Any] | None  # last successful generate_scenarios return
    usage: RunUsage
    messages: list[ModelMessage]
    flight_service: FakeFlightService
    accommodation_service: FakeAccommodationService
    research_service: FakeResearchService
    deps: AgentDependencies = field(repr=False, default=None)

    def calls_to(self, tool_name: str) -> list[ToolCall]:
        return [c for c in self.tool_calls if c.name == tool_name]

    @property
    def tool_names(self) -> list[str]:
        return [c.name for c in self.tool_calls]


def _clarifying_toolset(answer: str | None) -> FunctionToolset:
    """A scripted stand-in for the frontend `ask_clarifying_question` HITL tool.

    In production this tool lives in the browser (CopilotKit useHumanInTheLoop)
    and is exposed to the agent by the AG-UI adapter; headless it wouldn't
    exist and any call to it would burn the run's output retries. The stub
    keeps the tool surface identical to prod and answers deterministically:
    a scripted per-case answer, else the first offered option, else a nudge
    to decide autonomously.
    """
    async def ask_clarifying_question(
        question: str,
        options: list[str] | None = None,
        allow_multiple: bool = False,
    ) -> str:
        """Ask the traveler ONE focused clarifying question when required trip
        info is missing or ambiguous. Returns the traveler's answer as text."""
        if answer is not None:
            return answer
        if options:
            return options[0]
        return "No preference - please decide sensibly and continue."

    toolset = FunctionToolset()
    toolset.add_function(ask_clarifying_question, takes_ctx=False)
    return toolset


def _args_as_dict(part: ToolCallPart) -> dict[str, Any]:
    args = part.args
    if args is None:
        return {}
    if isinstance(args, str):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {"_raw": args}
    return dict(args)


def _extract(messages: list[ModelMessage]) -> tuple[list[ToolCall], dict[str, list[Any]]]:
    calls: list[ToolCall] = []
    returns: dict[str, list[Any]] = {}
    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    calls.append(ToolCall(name=part.tool_name, args=_args_as_dict(part)))
        elif isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart):
                    returns.setdefault(part.tool_name, []).append(part.content)
    return calls, returns


async def run_case(
    prompt: str,
    *,
    preferences: UserPreferences | None = None,
    message_history: list[ModelMessage] | None = None,
    model: Any = None,
    clarifying_answer: str | None = None,
) -> EvalRunResult:
    """Run one eval case headless and return an inspectable result.

    Args:
        prompt: The user's message for this turn.
        preferences: Seed preferences (stands in for the saved global profile).
        message_history: Prior turns for multi-turn cases.
        model: Optional model override; defaults to the agent's configured
            production model (settings.LLM_MODEL).
        clarifying_answer: Scripted reply for `ask_clarifying_question`; when
            None the stub answers with the first offered option.
    """
    flight_service = FakeFlightService()
    accommodation_service = FakeAccommodationService()
    research_service = FakeResearchService()
    deps = AgentDependencies(
        prompt_service=FilePromptService(_PROMPTS_DIR),
        user_preferences=preferences or UserPreferences(),
        flight_service=flight_service,
        accommodation_service=accommodation_service,
        research_service=research_service,
        # No DB repositories: profile persistence is a no-op in evals.
    )

    run_kwargs: dict[str, Any] = {
        "deps": deps,
        "usage_limits": _USAGE_LIMITS,
        "model_settings": _MODEL_SETTINGS,
        "toolsets": [_clarifying_toolset(clarifying_answer)],
    }
    if message_history is not None:
        run_kwargs["message_history"] = message_history
    if model is not None:
        run_kwargs["model"] = model

    result = await kompass_agent.run(prompt, **run_kwargs)

    messages = result.all_messages()
    tool_calls, tool_returns = _extract(messages)

    # The last generate_scenarios return that actually carried scenarios (the
    # tool returns {"error": ..., "scenarios": []} on validation rejections).
    scenarios_payload = next(
        (
            payload
            for payload in reversed(tool_returns.get("generate_scenarios", []))
            if isinstance(payload, dict) and payload.get("scenarios")
        ),
        None,
    )

    return EvalRunResult(
        prompt=prompt,
        output=result.output,
        tool_calls=tool_calls,
        tool_returns=tool_returns,
        scenarios_payload=scenarios_payload,
        usage=result.usage,
        messages=messages,
        flight_service=flight_service,
        accommodation_service=accommodation_service,
        research_service=research_service,
        deps=deps,
    )


def _summarize(res: EvalRunResult) -> str:
    lines = [f"PROMPT: {res.prompt}", "", "TOOL CALLS:"]
    if not res.tool_calls:
        lines.append("  (none)")
    for i, call in enumerate(res.tool_calls, 1):
        compact = {
            k: (f"[{len(v)} scenarios]" if k == "scenarios" and isinstance(v, list) else v)
            for k, v in call.args.items()
        }
        lines.append(f"  {i:2d}. {call.name}({json.dumps(compact, default=str)})")
    if res.scenarios_payload:
        lines.append("")
        lines.append("SCENARIOS PAYLOAD:")
        for s in res.scenarios_payload["scenarios"]:
            cb = s.get("cost_breakdown", {})
            lines.append(
                f"  - {s.get('comparison_label') or s.get('label')}: "
                f"{s.get('start_date')}..{s.get('end_date')}, "
                f"travelers={s.get('travelers')}, "
                f"total={cb.get('grand_total')} {res.scenarios_payload.get('currency')}, "
                f"stress={s.get('stress_score')}, "
                f"days={len(s.get('itinerary', {}).get('days', []))}"
            )
        lines.append(f"  estimated={res.scenarios_payload.get('estimated')}")
    lines.append("")
    lines.append(f"USAGE: {res.usage}")
    lines.append("")
    lines.append("FINAL TEXT:")
    lines.append(res.output)
    return "\n".join(lines)


async def _main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else (
        "Plan a weekend in Lisbon from Berlin, Sep 18-21 2026, 2 people, "
        "under 900 EUR total. I don't need any clarifications - decide sensibly."
    )
    res = await run_case(prompt)
    print(_summarize(res))


if __name__ == "__main__":
    asyncio.run(_main())
