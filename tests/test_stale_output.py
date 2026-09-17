"""A failed run must not leave a previous run's passing lesson on disk.

Regression test for a real bug found during development: run N passed and wrote
final_lesson.md; run N+1 exhausted its retries and escalated, but the old file
stayed. The outputs directory then showed a shipped lesson for a run that had
explicitly refused to approve one -- which is how stale content reaches learners.
"""

from __future__ import annotations

import lesson_agent.nodes.finalize as finalize_mod
from lesson_agent.models.evaluation import Attempt, GateResult, Verdict
from lesson_agent.state import initial_state


def _failing_state():
    v = Verdict(
        gates=[
            GateResult(gate_id="G1", passed=False, reasoning="jargon",
                       evidence="dense vector", fix_instruction="define it"),
            GateResult(gate_id="G7", passed=True, reasoning="ok"),
        ],
        summary="still failing",
    )
    s = initial_state("Introduction to RAG", "beginner", max_retries=2)
    s["attempt"] = 3
    s["verdict"] = v
    s["lesson"] = "a draft that never passed"
    s["history"] = [Attempt(attempt_number=3, lesson="a draft that never passed", verdict=v)]
    return s


def test_escalation_removes_a_stale_passing_lesson(tmp_path, monkeypatch):
    monkeypatch.setattr(finalize_mod, "OUTPUT_DIR", tmp_path)
    stale = tmp_path / "final_lesson.md"
    stale.write_text("lesson from an earlier run that DID pass", encoding="utf-8")

    finalize_mod.flag_for_human(_failing_state())

    assert not stale.exists(), "a failed run left a previous run's lesson on disk"


def test_escalation_still_writes_the_rejection_log(tmp_path, monkeypatch):
    """Removing the stale lesson must not remove the audit trail."""
    monkeypatch.setattr(finalize_mod, "OUTPUT_DIR", tmp_path)

    out = finalize_mod.flag_for_human(_failing_state())

    assert (tmp_path / "rejection_log.json").exists()
    assert (tmp_path / "run_summary.json").exists()
    assert out["status"] == "failed_needs_human"
    assert "G1" in out["human_review_reason"]


def test_escalation_with_no_prior_lesson_is_fine(tmp_path, monkeypatch):
    """The common case: nothing to clean up, and no crash."""
    monkeypatch.setattr(finalize_mod, "OUTPUT_DIR", tmp_path)
    finalize_mod.flag_for_human(_failing_state())
    assert not (tmp_path / "final_lesson.md").exists()


def test_sample_run_does_not_inherit_a_longer_previous_run(tmp_path, monkeypatch):
    """A 2-attempt run must not leave attempt_3.md from an earlier 3-attempt run.

    Second regression from the same family as the stale-lesson bug: outputs were
    written over the top of a previous run instead of replacing it, so the
    evidence directory could disagree with its own run_summary.json.
    """
    monkeypatch.setattr(finalize_mod, "OUTPUT_DIR", tmp_path)
    run_dir = tmp_path / "sample_run"
    run_dir.mkdir()
    (run_dir / "attempt_3.md").write_text("stale draft from a longer run", encoding="utf-8")
    (run_dir / "evaluation_3.json").write_text("{}", encoding="utf-8")

    v = Verdict(gates=[GateResult(gate_id=f"G{i}", passed=True, reasoning="ok")
                       for i in range(1, 8)], summary="good")
    s = initial_state("Introduction to RAG", "beginner", max_retries=2)
    s["attempt"] = 2
    s["verdict"] = v
    s["lesson"] = "the passing lesson"
    s["history"] = [
        Attempt(attempt_number=1, lesson="draft 1", verdict=v),
        Attempt(attempt_number=2, lesson="draft 2", verdict=v),
    ]

    finalize_mod.finalize(s)

    assert not (run_dir / "attempt_3.md").exists(), "stale third attempt survived"
    assert not (run_dir / "evaluation_3.json").exists()
    assert (run_dir / "attempt_1.md").exists()
    assert (run_dir / "attempt_2.md").exists()
