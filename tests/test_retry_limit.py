"""The loop must always terminate.

The brief requires "max 1-2 retries, so the loop always terminates". An agentic
loop whose exit condition is 'until the judge is happy' can run forever and bill
forever. These tests pin the termination guarantee.

The LLM nodes are stubbed, so this runs offline and deterministically -- we are
testing the control flow, which is ours, not the model, which is not.
"""

from __future__ import annotations

import pytest

from lesson_agent.graph import build_graph, route_after_evaluation
from lesson_agent.models.evaluation import Attempt, GateResult, Verdict
from lesson_agent.state import initial_state

ALL_GATES = [f"G{i}" for i in range(1, 8)]


def _verdict(passed: bool) -> Verdict:
    if passed:
        gates = [GateResult(gate_id=g, passed=True, reasoning="ok") for g in ALL_GATES]
    else:
        gates = [GateResult(gate_id=ALL_GATES[0], passed=False, reasoning="jargon",
                            evidence="dense vector", fix_instruction="define it")]
        gates += [GateResult(gate_id=g, passed=True, reasoning="ok") for g in ALL_GATES[1:]]
    return Verdict(gates=gates, summary="stub")


def _state(attempt: int, passed: bool, max_retries: int = 2):
    s = initial_state("T", "A", max_retries)
    s["attempt"] = attempt
    s["verdict"] = _verdict(passed)
    return s


# --- the router in isolation -------------------------------------------------

def test_passing_verdict_ships_immediately():
    assert route_after_evaluation(_state(1, True)) == "ship"


def test_failure_with_budget_left_retries():
    assert route_after_evaluation(_state(1, False)) == "retry"
    assert route_after_evaluation(_state(2, False)) == "retry"


def test_failure_at_the_budget_ceiling_escalates_rather_than_looping():
    """3 generations used with max_retries=2 — the budget is spent."""
    assert route_after_evaluation(_state(3, False)) == "escalate"


def test_failing_content_never_ships():
    """There is no path from a failed verdict to 'ship'. This is the core safety
    property: the system must never route bad content to the learner."""
    for attempt in range(1, 8):
        assert route_after_evaluation(_state(attempt, False)) != "ship"


def test_zero_retries_means_one_shot():
    assert route_after_evaluation(_state(1, False, max_retries=0)) == "escalate"


def test_router_refuses_to_decide_without_a_verdict():
    """A missing verdict must raise, never default to shipping."""
    s = initial_state("T", "A", 2)
    s["attempt"] = 1
    with pytest.raises(RuntimeError):
        route_after_evaluation(s)


# --- the whole graph, with the models stubbed out ----------------------------

@pytest.fixture
def always_failing_graph(monkeypatch):
    """A generator and an evaluator that can never succeed.

    If termination depended on the content ever being good, this would hang.
    """
    calls = {"generate": 0, "evaluate": 0}

    def fake_generate(state):
        calls["generate"] += 1
        n = state.get("attempt", 0) + 1
        history = list(state.get("history", []))
        history.append(Attempt(attempt_number=n, lesson=f"draft {n}", changed_on_retry=None))
        return {**state, "lesson": f"draft {n}", "attempt": n, "history": history, "verdict": None}

    def fake_evaluate(state):
        calls["evaluate"] += 1
        v = _verdict(False)
        history = list(state.get("history", []))
        if history:
            history[-1] = history[-1].model_copy(update={"verdict": v})
        return {**state, "verdict": v, "history": history}

    import lesson_agent.graph as graph_mod
    monkeypatch.setattr(graph_mod, "generate", fake_generate)
    monkeypatch.setattr(graph_mod, "evaluate", fake_evaluate)
    monkeypatch.setattr(graph_mod, "load_memory", lambda s: {**s, "known_failures": []})
    monkeypatch.setattr(graph_mod, "persist_memory", lambda s: s)
    monkeypatch.setattr(graph_mod, "finalize", lambda s: {**s, "status": "passed"})

    # Stub the escalation node too. The real one writes to outputs/, and the
    # committed sample_run/ is evidence of a genuine run -- a test must never
    # overwrite it with stub drafts.
    def fake_flag(state):
        return {**state, "status": "failed_needs_human",
                "human_review_reason": "stubbed escalation"}

    monkeypatch.setattr(graph_mod, "flag_for_human", fake_flag)
    return calls


def test_graph_terminates_when_content_never_passes(always_failing_graph):
    app = build_graph()
    state = initial_state("Introduction to RAG", "beginner", max_retries=2)
    final = app.invoke(state, {"recursion_limit": 25})

    assert final["status"] == "failed_needs_human"
    assert always_failing_graph["generate"] == 3   # 1 draft + 2 retries, no more
    assert always_failing_graph["evaluate"] == 3
    assert final["human_review_reason"]


def test_retry_budget_is_configurable(always_failing_graph):
    app = build_graph()
    state = initial_state("T", "A", max_retries=1)
    final = app.invoke(state, {"recursion_limit": 25})
    assert always_failing_graph["generate"] == 2   # 1 draft + 1 retry
    assert final["status"] == "failed_needs_human"
