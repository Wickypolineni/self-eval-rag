"""Structured evaluation output.

The central design decision here: a failed gate MUST carry a verbatim quote from
the lesson. This is enforced by a model validator, not by politeness in a prompt.

Why it matters: the standard objection to LLM-as-judge is that the judge simply
agrees with the generator. A judge that must locate and quote the offending span
cannot rubber-stamp -- there is nothing to quote if the fault is imagined, and a
fabricated quote is detectable because we check it appears in the lesson text.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class GateResult(BaseModel):
    """One binary gate. No partial credit -- it passed or it did not."""

    gate_id: str = Field(description="Gate identifier, e.g. 'G1'")
    passed: bool = Field(description="True only if the lesson fully satisfies this gate")
    reasoning: str = Field(
        description="One or two sentences explaining the judgement."
    )
    evidence: str | None = Field(
        default=None,
        description=(
            "REQUIRED when passed is false. A verbatim quote from the lesson showing "
            "the problem. Copy the text exactly; do not paraphrase. When passed is "
            "true, leave this null."
        ),
    )
    fix_instruction: str | None = Field(
        default=None,
        description=(
            "REQUIRED when passed is false. A specific, actionable instruction telling "
            "the writer what to change. Not 'improve clarity' but 'define the word "
            "embedding in plain language before using it in the retrieval section'."
        ),
    )

    @model_validator(mode="after")
    def _failures_must_cite(self) -> GateResult:
        """A failure without evidence is an opinion, not a finding."""
        if not self.passed:
            if not (self.evidence or "").strip():
                raise ValueError(
                    f"Gate {self.gate_id} failed but cited no evidence. "
                    "Every failure must quote the offending text."
                )
            if not (self.fix_instruction or "").strip():
                raise ValueError(
                    f"Gate {self.gate_id} failed but gave no fix instruction. "
                    "Every failure must say what to change."
                )
        return self


class Verdict(BaseModel):
    """The evaluator's complete judgement on one draft."""

    gates: list[GateResult] = Field(
        description="One result per gate in the rubric. Include every gate."
    )
    advisory_scores: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "1-5 per advisory dimension. Diagnostics only -- these never affect "
            "the pass decision."
        ),
    )
    summary: str = Field(
        description="Two or three sentences on the draft's overall state."
    )

    @property
    def passed(self) -> bool:
        """Ship if and only if every gate passes. This is the whole contract."""
        return bool(self.gates) and all(g.passed for g in self.gates)

    @property
    def failed_gates(self) -> list[GateResult]:
        return [g for g in self.gates if not g.passed]

    def feedback_block(self) -> str:
        """Render failures as instructions for the next generation attempt.

        Passed back into the generator so retry N+1 is informed by exactly what
        went wrong in retry N -- never a bare 'try again'.
        """
        lines: list[str] = []
        for g in self.failed_gates:
            lines.append(f"### {g.gate_id} FAILED - {g.reasoning}")
            lines.append(f'  Offending text: "{g.evidence}"')
            lines.append(f"  Required fix:   {g.fix_instruction}")
            lines.append("")
        return "\n".join(lines).strip()


class Attempt(BaseModel):
    """One trip around the loop, retained for the rejection log."""

    attempt_number: int
    lesson: str
    verdict: Verdict | None = None
    changed_on_retry: str | None = Field(
        default=None,
        description=(
            "What the generator changed relative to the previous attempt. The "
            "assessment brief requires the rejection log to record this; it is "
            "null on the first attempt because there is nothing prior."
        ),
    )

    def failed_gate_ids(self) -> list[str]:
        return [g.gate_id for g in self.verdict.failed_gates] if self.verdict else []


class GeneratedLesson(BaseModel):
    """Generator output. Paired so the lesson and its changelog arrive together."""

    lesson: str = Field(description="The complete lesson in Markdown.")
    changed_on_retry: str | None = Field(
        default=None,
        description=(
            "On a retry, a short account of what was changed in response to each "
            "failed gate. Null on the first attempt."
        ),
    )


RunStatus = Literal["generating", "passed", "failed_needs_human"]
