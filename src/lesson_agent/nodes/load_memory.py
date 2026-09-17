"""LOAD_MEMORY — pull cross-run failure patterns in before writing anything."""

from __future__ import annotations

from lesson_agent.memory import store
from lesson_agent.state import LessonState
from lesson_agent.utils import logging as log


def load_memory(state: LessonState) -> LessonState:
    warnings = store.known_failure_warnings()
    data = store.load()
    log.node("LOAD_MEMORY", f"{data.get('total_runs', 0)} previous run(s) on record")
    if warnings:
        log.info(f"{len(warnings)} repeated failure pattern(s) will be fed to the generator:")
        for w in warnings:
            log.dim(f"• {w}")
    else:
        log.dim("no repeated patterns yet — generator starts from the base prompt")
    return {**state, "known_failures": warnings}
