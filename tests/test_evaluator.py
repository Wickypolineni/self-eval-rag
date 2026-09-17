"""The evaluator's integrity properties.

These test the parts that must hold regardless of which model is behind the
judge: that a failure cannot be uncited, that a hallucinated citation is caught,
and that the pass condition is genuinely all-or-nothing.

No API key and no network required. A test suite that costs money to run is a
test suite nobody runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from lesson_agent.models.evaluation import GateResult, Verdict
from lesson_agent.nodes.evaluate import _quote_appears_in

FIXTURE = Path(__file__).parent / "fixtures" / "flawed_lesson.md"


def _fail(gate_id: str, evidence: str = "some quoted text", fix: str = "fix it") -> GateResult:
    return GateResult(gate_id=gate_id, passed=False, reasoning="r", evidence=evidence, fix_instruction=fix)


def _pass(gate_id: str) -> GateResult:
    return GateResult(gate_id=gate_id, passed=True, reasoning="fine")


# --- the judge must cite -----------------------------------------------------

def test_failure_without_evidence_is_rejected():
    """An uncited failure is an opinion, not a finding."""
    with pytest.raises(ValidationError):
        GateResult(gate_id="G1", passed=False, reasoning="too much jargon")


def test_failure_without_fix_instruction_is_rejected():
    with pytest.raises(ValidationError):
        GateResult(gate_id="G1", passed=False, reasoning="jargon", evidence="dense vector")


def test_passing_gate_needs_no_evidence():
    assert _pass("G2").evidence is None


# --- the pass condition is all-or-nothing ------------------------------------

def test_one_failed_gate_blocks_the_lesson():
    """No averaging, no compensation: six passes and one fail is a reject."""
    gates = [_pass(f"G{i}") for i in range(1, 7)] + [_fail("G7")]
    assert Verdict(gates=gates, summary="s").passed is False


def test_all_gates_passing_ships():
    gates = [_pass(f"G{i}") for i in range(1, 8)]
    assert Verdict(gates=gates, summary="s").passed is True


def test_empty_verdict_never_passes():
    """A verdict with no gates must not be read as success."""
    assert Verdict(gates=[], summary="s").passed is False


def test_advisory_scores_cannot_rescue_a_failed_gate():
    """Advisory scores are diagnostics. They must not affect shipping."""
    gates = [_pass(f"G{i}") for i in range(1, 7)] + [_fail("G7")]
    v = Verdict(
        gates=gates,
        advisory_scores={"beginner_friendliness": 5, "teaching_flow": 5,
                         "example_quality": 5, "concision": 5},
        summary="beautifully written but incomplete",
    )
    assert v.passed is False


# --- citation verification ---------------------------------------------------

def test_real_quote_from_the_flawed_fixture_is_verified():
    lesson = FIXTURE.read_text(encoding="utf-8")
    assert _quote_appears_in("a dense vector representation", lesson)
    assert _quote_appears_in("the bread and butter", lesson)


def test_hallucinated_quote_is_rejected():
    """The judge cannot invent evidence for a failure."""
    lesson = FIXTURE.read_text(encoding="utf-8")
    assert not _quote_appears_in(
        "RAG is a simple idea that anyone can understand in five minutes", lesson
    )


def test_quote_matching_tolerates_whitespace_and_case():
    lesson = FIXTURE.read_text(encoding="utf-8")
    assert _quote_appears_in("A  DENSE   vector  representation", lesson)


def test_empty_quote_is_not_a_citation():
    assert not _quote_appears_in("", "any lesson text")


# --- feedback routed back to the generator -----------------------------------

def test_feedback_block_carries_quote_and_fix():
    """Retry N+1 must receive the specific reason, never a bare 'try again'."""
    v = Verdict(
        gates=[_pass("G2"), _fail("G1", evidence="latent semantic space",
                                  fix="define 'vector' in plain words first")],
        summary="s",
    )
    block = v.feedback_block()
    assert "G1" in block
    assert "latent semantic space" in block
    assert "define 'vector' in plain words first" in block
    assert "G2" not in block  # passing gates are not noise in the retry prompt


# --- absence failures, and schema robustness --------------------------------

def test_a_missing_requirement_can_be_reported_without_a_quote():
    """Regression: coverage gates fail because something is ABSENT.

    Requiring a verbatim quote for every failure made missing content
    unreportable, and the evaluator prompt resolved that contradiction by
    passing the gate -- silently approving lessons with no worked example.
    """
    g = GateResult(
        gate_id="G4", passed=False, reasoning="no worked example",
        evidence_type="missing_requirement",
        evidence="no worked example appears anywhere in the lesson",
        fix_instruction="add one tracing a real question end to end",
    )
    assert g.passed is False
    assert g.evidence_type == "missing_requirement"


def test_a_missing_requirement_still_needs_a_statement_of_what_is_absent():
    with pytest.raises(ValidationError):
        GateResult(gate_id="G4", passed=False, reasoning="bad",
                   evidence_type="missing_requirement", fix_instruction="fix")


@pytest.mark.parametrize("sent", [None, "null", "", "Quoted-Span", "missing", "MISSING_REQUIREMENT"])
def test_evidence_type_tolerates_what_models_actually_send(sent):
    """A passing gate has no evidence, so judges routinely send null here.

    A strict Literal rejected the entire verdict over it -- failing all seven
    gates on a field that is meaningless when a gate passes.
    """
    g = GateResult(gate_id="G1", passed=True, reasoning="ok", evidence_type=sent)
    assert g.evidence_type in ("quoted_span", "missing_requirement")
