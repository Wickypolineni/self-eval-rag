"""EVALUATE — judges a draft against the binary gates.

Three properties make this evaluator worth trusting:

1. GROUNDED. Factual accuracy is checked against grounding/rag_reference.md,
   not against the judge's own recollection. Without a source of truth, "is
   this accurate?" is just one model's opinion of another model's output.

2. FORCED TO CITE. Every failure must quote the offending span verbatim. The
   schema rejects an uncited failure, and we verify the quote actually occurs
   in the lesson. A judge that must point at the problem cannot rubber-stamp.

3. A DIFFERENT VENDOR from the generator. A model grades its own prose more
   softly than a stranger's.

Parse failures here are FATAL. A verdict that does not parse must never be
treated as a pass -- silently shipping unjudged content is the one failure mode
this whole system exists to prevent.
"""

from __future__ import annotations

import difflib

from langchain_core.messages import HumanMessage, SystemMessage

from lesson_agent.models.evaluation import GateResult, Verdict
from lesson_agent.nodes.prechecks import run_prechecks
from lesson_agent.state import LessonState
from lesson_agent.utils import logging as log
from lesson_agent.utils.config import (
    gate_ids,
    load_grounding,
    load_prompts,
    load_rubric,
    render_rubric_for_prompt,
)
from lesson_agent.utils.llm import evaluator_model
from lesson_agent.utils.text import fill


class EvaluationError(RuntimeError):
    """The verdict could not be trusted. Never downgrade this to a pass."""


class _UnverifiableVerdict(RuntimeError):
    """Internal: the verdict cited text that is not in the lesson. Re-request it."""


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


def _quote_appears_in(quote: str, lesson: str) -> bool:
    """Verify a cited quote is really in the lesson.

    Models paraphrase when asked to copy, so an exact check alone would be too
    strict. We allow close fuzzy matches but reject citations that are
    substantially invented.
    """
    q, l = _normalise(quote), _normalise(lesson)
    if not q:
        return False
    if q in l:
        return True
    # Fall back to a similarity check against the closest window in the lesson.
    window = len(q)
    if window > len(l):
        return False
    best = 0.0
    step = max(1, window // 4)
    for i in range(0, len(l) - window + 1, step):
        ratio = difflib.SequenceMatcher(None, q, l[i : i + window]).ratio()
        best = max(best, ratio)
        if best >= 0.75:
            return True
    return False


def _gate_names() -> dict[str, str]:
    return {g["id"]: g["name"] for g in load_rubric()["gates"]}


def evaluate(state: LessonState) -> LessonState:
    log.node("EVALUATE", f"judging attempt {state['attempt']} against {len(gate_ids())} binary gates")

    prompts = load_prompts()["evaluator"]
    user_prompt = fill(
        prompts["user"],
        audience=state["audience"],
        grounding=load_grounding(),
        rubric=render_rubric_for_prompt(),
        lesson=state["lesson"] or "",
    )

    model = evaluator_model()
    structured = model.with_structured_output(Verdict, include_raw=True)
    lesson_text = state["lesson"] or ""
    names = _gate_names()

    def _request_verdict() -> Verdict:
        """One round trip, fully validated. Raises if it cannot be trusted."""
        result = structured.invoke([
            SystemMessage(content=prompts["system"]),
            HumanMessage(content=user_prompt),
        ])
        parsed = result.get("parsed")
        if parsed is None:
            raise EvaluationError(
                f"evaluator returned unparseable output: "
                f"{str(result.get('parsing_error') or 'no parsed object')[:300]}"
            )

        # Every gate must be judged. A partial pass is not a verdict.
        if missing := set(gate_ids()) - {g.gate_id for g in parsed.gates}:
            raise _UnverifiableVerdict(f"evaluator skipped gate(s): {sorted(missing)}")

        # Only quoted_span failures claim something about the lesson's literal
        # text. A missing_requirement describes what is ABSENT -- there is
        # nothing to locate, so nothing to verify.
        unverifiable = [
            g.gate_id
            for g in parsed.gates
            if not g.passed
            and g.evidence_type == "quoted_span"
            and g.evidence
            and not _quote_appears_in(g.evidence, lesson_text)
        ]
        if unverifiable:
            raise _UnverifiableVerdict(
                f"cited text absent from the lesson on: {', '.join(unverifiable)}"
            )
        return parsed

    # Two attempts, then fail loud.
    #
    # An earlier version flipped an unverifiable failure to passed, on the
    # reasoning that a hallucinated citation should not drive a pointless
    # retry. That was fail-open: a judge that merely quoted sloppily could
    # approve content it had just rejected. A verdict we cannot verify is a
    # verdict we cannot use, so it is discarded whole and re-requested -- and
    # if the second attempt is also untrustworthy, the run stops. Shipping on
    # an unreadable verdict is the one outcome this system exists to prevent.
    verdict: Verdict | None = None
    last_error: Exception | None = None
    for attempt_n in range(2):
        try:
            verdict = _request_verdict()
            break
        except Exception as exc:  # noqa: BLE001 - re-raised below if terminal
            last_error = exc
            if attempt_n == 0:
                log.warn(f"verdict rejected ({type(exc).__name__}: {str(exc)[:120]}); re-requesting once")

    if verdict is None:
        raise EvaluationError(
            "Evaluator failed to produce a trustworthy verdict after a retry. "
            "Refusing to treat an unusable verdict as a pass.\n"
            f"Last error: {last_error}"
        ) from last_error

    # --- Deterministic prechecks override the judge ------------------------
    # The LLM judge has a demonstrated false-negative rate: it passed a
    # sabotaged draft on G1 and G6 while scoring that same draft 1-2 out of 5
    # on its own advisory dimensions. Where a gate can be measured instead of
    # judged, the measurement wins. A precheck can only FAIL a gate, never
    # pass one -- it is a floor under the judge, not a replacement for it.
    precheck_failures = run_prechecks(lesson_text)
    if precheck_failures:
        by_gate = {g.gate_id: g for g in precheck_failures}
        overridden: list[str] = []
        merged: list[GateResult] = []
        for g in verdict.gates:
            if (pre := by_gate.get(g.gate_id)) is not None:
                if g.passed:
                    overridden.append(g.gate_id)
                merged.append(pre)
            else:
                merged.append(g)
        verdict = verdict.model_copy(update={"gates": merged})
        if overridden:
            log.warn(
                f"deterministic precheck overrode the judge on {', '.join(overridden)} "
                "— the model passed text that fails an objective check"
            )

    # --- Report -------------------------------------------------------------
    for g in verdict.gates:
        name = names.get(g.gate_id, "")
        if g.passed:
            log.gate_pass(g.gate_id, name)
        else:
            log.gate_fail(g.gate_id, name, g.evidence or "", g.fix_instruction or "")

    if verdict.advisory_scores:
        scores = "  ".join(f"{k}={v}" for k, v in verdict.advisory_scores.items())
        log.dim(f"advisory (not ship-blocking): {scores}")

    log.verdict_line(verdict.passed, len(verdict.failed_gates), len(verdict.gates))

    history = list(state.get("history", []))
    if history:
        history[-1] = history[-1].model_copy(update={"verdict": verdict})

    return {
        **state,
        "verdict": verdict,
        "history": history,
        "status": "passed" if verdict.passed else "generating",
    }
