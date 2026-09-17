"""GENERATE — writes the first draft and every retry.

One node, one code path. A retry is not a different operation: it is the same
generation with the previous draft and its specific failures added to the
prompt. Splitting this into generate/regenerate would create two prompt paths
that drift apart, two edges into evaluation, and two places to forget to inject
memory.

What distinguishes retry N from retry N-1 is the content of the prompt, not the
code that builds it.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from lesson_agent.memory import store
from lesson_agent.models.evaluation import Attempt, GeneratedLesson
from lesson_agent.state import LessonState
from lesson_agent.utils import logging as log
from lesson_agent.utils.config import load_prompts
from lesson_agent.utils.llm import generator_model
from lesson_agent.utils.text import fill


def generate(state: LessonState) -> LessonState:
    prompts = load_prompts()["generator"]
    attempt = int(state.get("attempt", 0)) + 1
    is_retry = attempt > 1

    memory_text = store.memory_block(state.get("known_failures") or [])

    if is_retry:
        previous = state["history"][-1]
        log.node("GENERATE", f"attempt {attempt} — revising against {len(previous.failed_gate_ids())} failed gate(s)")
        log.dim(f"addressing: {', '.join(previous.failed_gate_ids())}")
        user_prompt = fill(
            prompts["retry"],
            topic=state["topic"],
            previous_lesson=previous.lesson,
            feedback=previous.verdict.feedback_block(),
            memory_block=memory_text,
        )
    else:
        log.node("GENERATE", f"attempt {attempt} — first draft")
        if memory_text:
            log.dim("injecting cross-run memory into the prompt")
        user_prompt = fill(
            prompts["first_draft"],
            topic=state["topic"],
            memory_block=memory_text,
        )

    system_prompt = fill(prompts["system"], audience=state["audience"])

    model = generator_model()
    structured = model.with_structured_output(GeneratedLesson, include_raw=True)
    result = structured.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    parsed: GeneratedLesson | None = result.get("parsed")
    if parsed is None:
        # A generator parse failure is recoverable: fall back to the raw text as
        # the lesson. We lose the changelog, not the safety property -- the
        # evaluator still judges whatever comes out. (Contrast evaluate.py,
        # where a parse failure MUST be fatal.)
        raw = result.get("raw")
        text = getattr(raw, "content", "") or ""
        log.warn("generator returned unstructured output; using raw text, changelog unavailable")
        parsed = GeneratedLesson(lesson=str(text).strip(), changed_on_retry=None)

    log.info(f"produced {len(parsed.lesson.split())} words")
    if parsed.changed_on_retry:
        log.dim(f"changes: {parsed.changed_on_retry[:200]}")

    history = list(state.get("history", []))
    history.append(Attempt(
        attempt_number=attempt,
        lesson=parsed.lesson,
        verdict=None,
        changed_on_retry=parsed.changed_on_retry,
    ))

    return {
        **state,
        "lesson": parsed.lesson,
        "changed_on_retry": parsed.changed_on_retry,
        "attempt": attempt,
        "history": history,
        "verdict": None,
        "status": "generating",
    }
