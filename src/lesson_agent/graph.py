"""The graph.

    load_memory → generate → evaluate → [ROUTER] ─pass─────→ finalize ──┐
                     ↑                      │                           ├→ persist_memory
                     └──────retry───────────┤                           │
                                            └─exhausted─→ flag_for_human┘

The router is the assessment. It is the point where the system decides, with no
human present, whether content is good enough to ship.

It is deliberately NOT an LLM call. It is three lines of Python reading a
boolean off the verdict. The intelligence belongs in judging the content; the
control flow stays deterministic so the same verdict always produces the same
routing decision, and so a curriculum lead can be told exactly why something
shipped.
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, StateGraph

from lesson_agent.nodes.evaluate import evaluate
from lesson_agent.nodes.finalize import finalize, flag_for_human, persist_memory
from lesson_agent.nodes.generate import generate
from lesson_agent.nodes.load_memory import load_memory
from lesson_agent.state import LessonState
from lesson_agent.utils import logging as log

Route = Literal["retry", "ship", "escalate"]


def route_after_evaluation(state: LessonState) -> Route:
    """The ship / don't-ship decision.

    Three outcomes, and the third is what makes the loop safe: when the retry
    budget is spent and the content still fails, we escalate rather than either
    shipping it or looping forever.
    """
    verdict = state.get("verdict")
    if verdict is None:
        raise RuntimeError("router reached with no verdict — evaluation did not run")

    if verdict.passed:
        log.route("SHIP", f"all {len(verdict.gates)} gates passed on attempt {state['attempt']}")
        return "ship"

    generations_used = int(state.get("attempt", 0))
    generations_allowed = int(state.get("max_retries", 2)) + 1
    failed = ", ".join(g.gate_id for g in verdict.failed_gates)

    if generations_used < generations_allowed:
        remaining = generations_allowed - generations_used
        log.route(
            "REGENERATE",
            f"failed {failed} · {remaining} attempt(s) left of {generations_allowed}",
        )
        return "retry"

    log.route("ESCALATE", f"still failing {failed} after {generations_used} attempts")
    return "escalate"


def build_graph():
    g = StateGraph(LessonState)

    g.add_node("load_memory", load_memory)
    g.add_node("generate", generate)
    g.add_node("evaluate", evaluate)
    g.add_node("finalize", finalize)
    g.add_node("flag_for_human", flag_for_human)
    g.add_node("persist_memory", persist_memory)

    g.set_entry_point("load_memory")
    g.add_edge("load_memory", "generate")
    g.add_edge("generate", "evaluate")

    # The conditional edge — the autonomous quality gate.
    g.add_conditional_edges(
        "evaluate",
        route_after_evaluation,
        {
            "retry": "generate",        # the cycle
            "ship": "finalize",
            "escalate": "flag_for_human",
        },
    )

    # Both terminal outcomes record what was learned. A failed run teaches the
    # system more than a passing one, so memory must not be skipped on failure.
    g.add_edge("finalize", "persist_memory")
    g.add_edge("flag_for_human", "persist_memory")
    g.add_edge("persist_memory", END)

    return g.compile()
