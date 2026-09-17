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
