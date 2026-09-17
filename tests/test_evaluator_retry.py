"""The evaluator must fail CLOSED.

This protects the most important fix in the repo. Two defects previously let a
verdict that could not be trusted turn into an approval:

  - a failure citing text absent from the lesson was flipped to passed
  - a verdict missing gates was treated as usable

Both are fail-open: the check could not do its job, so it approved. The rule is
that an untrustworthy verdict is discarded whole and re-requested once, and a
second untrustworthy verdict stops the run.

The model is mocked, so these run offline and deterministically. We are testing
our control flow, not the model.
"""

from __future__ import annotations

import pytest

import lesson_agent.nodes.evaluate as ev
from lesson_agent.models.evaluation import GateResult, Verdict
from lesson_agent.state import initial_state

LESSON = (
    "RAG helps a program answer better. It finds useful text first. "
    "Then it uses that text to write an answer for you."
)
ALL_GATES = [f"G{i}" for i in range(1, 8)]


def _verdict(*, failing: dict[str, str] | None = None, skip: str | None = None) -> Verdict:
    """failing maps gate_id -> the evidence string it will cite."""
    failing = failing or {}
    gates = []
    for gid in ALL_GATES:
        if gid == skip:
            continue
        if gid in failing:
            gates.append(GateResult(
                gate_id=gid, passed=False, reasoning="bad",
                evidence_type="quoted_span",
                evidence=failing[gid], fix_instruction="fix it",
            ))
        else:
            gates.append(GateResult(gate_id=gid, passed=True, reasoning="ok"))
    return Verdict(gates=gates, summary="stub")


class _FakeStructured:
    """Returns a queued verdict per invoke, recording how many calls happened."""

    def __init__(self, queue):
        self.queue = list(queue)
        self.calls = 0

    def invoke(self, _messages):
        self.calls += 1
        item = self.queue.pop(0) if self.queue else self.queue_last
        self.queue_last = item
        if isinstance(item, Verdict):
            return {"parsed": item, "raw": None, "parsing_error": None}
        return {"parsed": None, "raw": None, "parsing_error": item}


class _FakeModel:
    def __init__(self, structured):
        self._structured = structured

    def with_structured_output(self, *_a, **_k):
        return self._structured


@pytest.fixture
def evaluator(monkeypatch):
    def _install(queue):
        structured = _FakeStructured(queue)
        structured.queue_last = queue[-1]
        monkeypatch.setattr(ev, "evaluator_model", lambda: _FakeModel(structured))
        monkeypatch.setattr(ev, "run_prechecks", lambda _t: [])   # isolate the judge
        return structured
    return _install


def _state():
    s = initial_state("Introduction to RAG", "beginner", max_retries=2)
    s["attempt"] = 1
    s["lesson"] = LESSON
    s["history"] = []
    return s


# --- unverifiable citations --------------------------------------------------

def test_a_hallucinated_citation_triggers_exactly_one_retry(evaluator):
    """First verdict cites text not in the lesson; second is clean."""
    bad = _verdict(failing={"G1": "a sentence that never appears in this lesson"})
    good = _verdict()
    structured = evaluator([bad, good])

    out = ev.evaluate(_state())

    assert structured.calls == 2, "the untrustworthy verdict was not re-requested"
    assert out["verdict"].passed is True


def test_two_hallucinated_citations_fail_closed(evaluator):
    """The run must stop, never approve on an unverifiable verdict."""
    bad = _verdict(failing={"G1": "text that is definitely not in the lesson at all"})
    evaluator([bad, bad])

    with pytest.raises(ev.EvaluationError):
        ev.evaluate(_state())


def test_an_unverifiable_failure_is_never_converted_to_a_pass(evaluator):
    """Regression for the exact fail-open that existed: passed = True."""
    bad = _verdict(failing={"G1": "phantom text nowhere in the lesson body"})
    evaluator([bad, bad])

    with pytest.raises(ev.EvaluationError):
        ev.evaluate(_state())


def test_a_real_quote_is_accepted_without_retry(evaluator):
    """A genuine failure must not be second-guessed."""
    real = _verdict(failing={"G1": "It finds useful text first"})
    structured = evaluator([real])

    out = ev.evaluate(_state())

    assert structured.calls == 1
    assert out["verdict"].passed is False
    assert [g.gate_id for g in out["verdict"].failed_gates] == ["G1"]


# --- missing requirements need no quote --------------------------------------

def test_a_missing_requirement_is_not_checked_against_the_lesson(evaluator):
    """Absence cannot be quoted, so it must not be verified as a quote."""
    v = Verdict(
        gates=[GateResult(
            gate_id="G4", passed=False, reasoning="none present",
            evidence_type="missing_requirement",
            evidence="no worked example appears anywhere in the lesson",
            fix_instruction="add one",
        )] + [GateResult(gate_id=g, passed=True, reasoning="ok") for g in ALL_GATES if g != "G4"],
        summary="stub",
    )
    structured = evaluator([v])

    out = ev.evaluate(_state())

    assert structured.calls == 1, "an absence finding was wrongly treated as a quote"
    assert out["verdict"].passed is False


# --- incomplete verdicts ------------------------------------------------------

def test_a_skipped_gate_triggers_a_retry(evaluator):
    structured = evaluator([_verdict(skip="G3"), _verdict()])

    out = ev.evaluate(_state())

    assert structured.calls == 2
    assert out["verdict"].passed is True


def test_a_persistently_incomplete_verdict_fails_closed(evaluator):
    evaluator([_verdict(skip="G3"), _verdict(skip="G3")])

    with pytest.raises(ev.EvaluationError):
        ev.evaluate(_state())


# --- unparseable output -------------------------------------------------------

def test_an_unparseable_verdict_retries_then_raises(evaluator):
    structured = evaluator(["schema validation exploded", "schema validation exploded"])

    with pytest.raises(ev.EvaluationError):
        ev.evaluate(_state())
    assert structured.calls == 2


def test_an_unparseable_first_verdict_recovers_on_retry(evaluator):
    structured = evaluator(["bad json", _verdict()])

    out = ev.evaluate(_state())

    assert structured.calls == 2
    assert out["verdict"].passed is True


# --- prechecks still override a passing judge ---------------------------------

def test_a_precheck_failure_overrides_a_clean_verdict(monkeypatch, evaluator):
    """The deterministic floor must survive the retry restructuring."""
    evaluator([_verdict()])
    monkeypatch.setattr(ev, "run_prechecks", lambda _t: [GateResult(
        gate_id="G6", passed=False, reasoning="measured too long",
        evidence_type="quoted_span", evidence="It finds useful text first",
        fix_instruction="shorten",
    )])

    out = ev.evaluate(_state())

    assert out["verdict"].passed is False
    assert [g.gate_id for g in out["verdict"].failed_gates] == ["G6"]


# --- malformed gate sets ------------------------------------------------------

def test_a_duplicated_gate_triggers_a_retry(evaluator):
    """The same gate returned twice is ambiguous, not a verdict."""
    dup = _verdict()
    dup = dup.model_copy(update={"gates": dup.gates + [dup.gates[0]]})
    structured = evaluator([dup, _verdict()])

    out = ev.evaluate(_state())

    assert structured.calls == 2
    assert out["verdict"].passed is True


def test_an_invented_gate_triggers_a_retry(evaluator):
    from lesson_agent.models.evaluation import GateResult as GR
    bogus = _verdict()
    bogus = bogus.model_copy(update={
        "gates": bogus.gates + [GR(gate_id="G99", passed=True, reasoning="?")]
    })
    structured = evaluator([bogus, _verdict()])

    ev.evaluate(_state())

    assert structured.calls == 2
