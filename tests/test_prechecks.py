"""Deterministic prechecks, and the override that makes them matter.

Written after the LLM judge passed a deliberately sabotaged draft on G1 and G6
while scoring that same draft 1-2/5 on its own advisory dimensions. A gate that
can be talked out of a failure is not a gate.

Prechecks may only FAIL a gate, never pass one. They are a floor under the
judge, not a replacement for it.
"""

from __future__ import annotations

from lesson_agent.nodes.prechecks import (
    MAX_MEAN_SENTENCE_WORDS,
    MAX_SENTENCE_WORDS,
    _sentences,
    run_prechecks,
)

ACADEMIC = (
    "Retrieval-Augmented Generation emerges as a preeminent architectural paradigm "
    "addressing these challenges, seamlessly integrating non-parametric memory into "
    "the generative process while simultaneously leveraging the dense vector "
    "representation of linguistic units within a latent semantic space of fixed "
    "dimensionality to facilitate efficient retrieval."
)

PLAIN = (
    "RAG helps a computer program answer better.\n\n"
    "It finds useful text first. Then it uses that text to write an answer.\n\n"
    "Think of a student in a library. The student finds the right book. "
    "Then the student writes the answer.\n"
)


def _gate_ids(text: str) -> list[str]:
    return [r.gate_id for r in run_prechecks(text)]


def test_graduate_jargon_fails_g1():
    assert "G1" in _gate_ids(ACADEMIC)


def test_overlong_sentences_fail_g6():
    long_sentence = "This " + "very " * 60 + "long sentence continues without end."
    assert "G6" in _gate_ids(long_sentence)


def test_idioms_fail_g6():
    text = "RAG is not rocket science once you wrap your head around the basics. " * 2
    assert "G6" in _gate_ids(text)


def test_plain_beginner_prose_passes_everything():
    """The check must not punish the writing style we actually want."""
    assert run_prechecks(PLAIN) == []


def test_no_false_positive_on_the_shipped_lesson():
    """Guards against a precheck so strict it blocks acceptable content."""
    from pathlib import Path
    lesson = Path(__file__).parent.parent / "outputs" / "final_lesson.md"
    if lesson.exists():
        assert run_prechecks(lesson.read_text(encoding="utf-8")) == []


def test_one_failure_per_gate():
    """Several problems on one gate must not produce duplicate results."""
    text = ACADEMIC + " " + ACADEMIC
    ids = _gate_ids(text)
    assert len(ids) == len(set(ids))


def test_code_blocks_are_not_measured_as_prose():
    """A long line of code is not an unreadable sentence."""
    text = PLAIN + "\n```\n" + "x = " + " + ".join(str(i) for i in range(80)) + "\n```\n"
    assert "G6" not in _gate_ids(text)


def test_headings_and_lists_are_not_measured_as_prose():
    text = PLAIN + "\n- " + "item " * 50 + "\n"
    assert "G6" not in _gate_ids(text)


def test_sentence_splitter_ignores_fragments():
    assert all(len(s.split()) > 2 for s in _sentences(PLAIN))


def test_failures_carry_evidence_and_a_fix():
    """Same contract as the LLM judge: no uncited failures."""
    for r in run_prechecks(ACADEMIC):
        assert r.evidence and r.evidence.strip()
        assert r.fix_instruction and r.fix_instruction.strip()
        assert r.passed is False


def test_threshold_is_the_documented_one():
    """Must clear BOTH limits: the per-sentence cap and the mean."""
    ok = " ".join(["word"] * (MAX_MEAN_SENTENCE_WORDS - 5)) + "."
    assert "G6" not in _gate_ids(ok)


def test_a_single_overlong_sentence_fails_even_if_the_mean_is_fine():
    """One 46-word monster among short sentences must still fail."""
    text = "RAG is simple. It finds text. It writes answers. " + " ".join(["word"] * 46) + "."
    assert "G6" in _gate_ids(text)
