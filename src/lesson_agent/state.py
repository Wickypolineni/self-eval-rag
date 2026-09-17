"""The graph's shared state.

Every node reads from and writes to this one object. Keeping the full attempt
history in state -- not just the latest draft -- is what lets retry #2 be smarter
than retry #1: the generator sees the previous draft AND the specific reasons it
was rejected, rather than starting over blind.
"""

from __future__ import annotations

from typing import TypedDict

from lesson_agent.models.evaluation import Attempt, RunStatus, Verdict


class LessonState(TypedDict, total=False):
    # --- Inputs, fixed for the run ---
    topic: str
    audience: str

    # --- Current working values ---
    lesson: str | None
    verdict: Verdict | None
    changed_on_retry: str | None

    # --- Loop control ---
    attempt: int          # 1-indexed: attempt 1 is the first draft
    max_retries: int      # 2 retries => at most 3 generations
    status: RunStatus

    # --- Accumulated record ---
    history: list[Attempt]

    # --- Cross-run memory, loaded at start, persisted at end ---
    known_failures: list[str]

    # --- Escalation ---
    human_review_reason: str | None


def initial_state(
    topic: str,
    audience: str,
    max_retries: int,
    known_failures: list[str] | None = None,
) -> LessonState:
    return LessonState(
        topic=topic,
        audience=audience,
        lesson=None,
        verdict=None,
        changed_on_retry=None,
        attempt=0,
        max_retries=max_retries,
        status="generating",
        history=[],
        known_failures=known_failures or [],
        human_review_reason=None,
    )
