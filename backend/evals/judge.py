"""A small, structured LLM-as-judge for soft criteria a Python assert can't
capture (does the reply read as a recommendation? do the day activities match
the requested vibe?).

Kept deliberately narrow: the judge sees ONLY the focused slice each evaluator
hands it (the final reply, or a compact day-by-day digest) — never the whole
serialized trace — so prompts stay cheap, fast, and hard to game. The judge
runs on flash-lite by default: scoring a single boolean rubric is well within
flash-lite's ability and keeps eval cost low. Override with EVAL_JUDGE_MODEL
(flash-lite's empty-completion issues on large *synthesis* contexts don't apply
here — the judge only emits a tiny structured verdict).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_ai import Agent

# app.config is the credential boundary (exports GOOGLE_API_KEY to the env for
# the Gemini provider) and the source of the judge model setting. Importing it
# here means `evals.judge` works standalone regardless of import order. The
# judge model defaults to flash-lite and is decoupled from the agent-under-test
# so it never shifts just because prod's LLM_MODEL / RESEARCH_MODEL changes;
# override via the EVAL_JUDGE_MODEL env var (or backend/.env).
from app.config import settings


class Verdict(BaseModel):
    """A judge decision. `passed` is the assertion; `reason` aids debugging."""

    passed: bool = Field(description="True if the criterion is clearly met.")
    reason: str = Field(description="One concise sentence justifying the verdict.")


_JUDGE_INSTRUCTIONS = (
    "You are a strict evaluator of an AI travel planner's output. You are given "
    "a single criterion and the relevant slice of the assistant's response. "
    "Decide ONLY whether that criterion is clearly satisfied. Be conservative: "
    "if the evidence is ambiguous or missing, fail it. Judge the criterion as "
    "written — do not invent additional requirements. Respond with a boolean "
    "verdict and one concise sentence of justification."
)


@lru_cache(maxsize=1)
def _judge_agent() -> Agent:
    return Agent(
        model=settings.eval_judge_model,
        output_type=Verdict,
        instructions=_JUDGE_INSTRUCTIONS,
    )


async def judge(criterion: str, content: str) -> Verdict:
    """Return the judge's verdict on whether `content` satisfies `criterion`."""
    prompt = f"CRITERION:\n{criterion}\n\nRESPONSE SLICE:\n{content}"
    result = await _judge_agent().run(prompt)
    return result.output
