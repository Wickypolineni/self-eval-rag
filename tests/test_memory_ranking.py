"""Memory must warn about the gate that is blocking now, not the biggest pile.

Regression test for a real failure observed across runs 5-8: G5 ended two
consecutive runs in escalation, but the warnings fed to the generator were
G4/G2/G1/G3 -- gates with larger lifetime totals accumulated earlier. The gate
actually stopping content from shipping was never mentioned to the writer, so
the system kept relearning the same lesson and failing on the same thing.
"""

from __future__ import annotations

from lesson_agent.memory import store


def _rank(data):
    return [g for g, _total, _score in store._warning_ranking(data)]


def test_a_recent_blocker_outranks_a_larger_stale_pile():
    data = {
        # G1 has the biggest lifetime total, but all of it is old.
        "gate_failure_counts": {"G1": 20, "G5": 4},
        "run_history": [
            {"run": 1, "passed": True, "failed_gates": ["G1"]},
            {"run": 2, "passed": False, "failed_gates": ["G5"]},
            {"run": 3, "passed": False, "failed_gates": ["G5"]},
        ],
    }
    assert _rank(data)[0] == "G5", "the gate ending runs in escalation must rank first"


def test_escalation_outweighs_a_failure_that_got_fixed():
    """Failing once and recovering is less serious than failing terminally."""
    data = {
        "gate_failure_counts": {"G2": 6, "G5": 6},
        "run_history": [
            # G2 failed but the run recovered and shipped; G5 ended in escalation.
            {"run": 1, "passed": True, "failed_gates": ["G2"]},
            {"run": 2, "passed": False, "failed_gates": ["G5"]},
        ],
    }
    assert _rank(data)[0] == "G5"


def test_ranking_is_stable_with_no_history():
    """Older memory files predate run_history; fall back to totals, don't crash."""
    data = {"gate_failure_counts": {"G1": 3, "G2": 7}}
    assert _rank(data) == ["G2", "G1"]


def test_empty_memory_produces_no_warnings():
    assert store._warning_ranking({}) == []


def test_single_failure_stays_below_the_warning_threshold(monkeypatch):
    """One failure is noise. Only a repeat is worth warning about."""
    monkeypatch.setattr(store, "load", lambda: {
        "gate_failure_counts": {"G1": 1},
        "run_history": [{"run": 1, "passed": True, "failed_gates": ["G1"]}],
        "recent_failures": [],
    })
    assert store.known_failure_warnings() == []
