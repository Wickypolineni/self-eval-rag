"""Terminal nodes: FINALIZE, FLAG_FOR_HUMAN, PERSIST_MEMORY.

The brief names the required output precisely: "the passing lesson + a rejection
log -- what failed, why, and what you changed on retry." All three fields are
written here.

Note that FLAG_FOR_HUMAN is a real outcome, not an error path. A system that
cannot say "I could not get this right, a person should look" would either ship
failing content or loop forever. Escalation is what makes the autonomy safe.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from lesson_agent.memory import store
from lesson_agent.state import LessonState
from lesson_agent.utils import logging as log
from lesson_agent.utils.llm import model_names

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "outputs"


def _rejection_log(state: LessonState) -> list[dict]:
    """what failed · why · what changed on retry — the three required fields."""
    entries: list[dict] = []
    for att in state.get("history", []):
        if att.verdict is None or att.verdict.passed:
            continue
        entries.append({
            "attempt": att.attempt_number,
            "what_failed": [g.gate_id for g in att.verdict.failed_gates],
            "why": [
                {
                    "gate_id": g.gate_id,
                    "reasoning": g.reasoning,
                    "evidence_quoted_from_lesson": g.evidence,
                    "required_fix": g.fix_instruction,
                }
                for g in att.verdict.failed_gates
            ],
            "changed_on_next_retry": _change_note(state, att.attempt_number),
        })
    return entries


def _change_note(state: LessonState, attempt_number: int) -> str | None:
    """The changelog belongs to the attempt that FOLLOWED this rejection."""
    for att in state.get("history", []):
        if att.attempt_number == attempt_number + 1:
            return att.changed_on_retry or "(generator did not report a changelog)"
    return None


def _write_outputs(state: LessonState) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_dir = OUTPUT_DIR / "sample_run"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Clear prior attempts before writing. A run that took 2 attempts must not
    # inherit attempt_3.md from an earlier 3-attempt run: the directory would
    # then contradict run_summary.json, and the evidence of what this run
    # actually did would be wrong.
    for old_file in run_dir.glob("attempt_*.md"):
        old_file.unlink()
    for old_file in run_dir.glob("evaluation_*.json"):
        old_file.unlink()

    for att in state.get("history", []):
        (run_dir / f"attempt_{att.attempt_number}.md").write_text(att.lesson, encoding="utf-8")
        if att.verdict is not None:
            (run_dir / f"evaluation_{att.attempt_number}.json").write_text(
                json.dumps(att.verdict.model_dump(), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    rejections = _rejection_log(state)
    (OUTPUT_DIR / "rejection_log.json").write_text(
        json.dumps(rejections, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    summary = {
        "topic": state["topic"],
        "status": state["status"],
        "attempts_used": state.get("attempt", 0),
        "max_generations_allowed": int(state.get("max_retries", 2)) + 1,
        "models": model_names(),
        "gates_failed_by_attempt": {
            str(a.attempt_number): a.failed_gate_ids() for a in state.get("history", [])
        },
        "human_review_reason": state.get("human_review_reason"),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (OUTPUT_DIR / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def finalize(state: LessonState) -> LessonState:
    log.node("FINALIZE", "all gates passed — lesson is cleared to ship")
    _write_outputs(state)
    (OUTPUT_DIR / "final_lesson.md").write_text(state["lesson"] or "", encoding="utf-8")
    log.info(f"wrote outputs/final_lesson.md ({len((state['lesson'] or '').split())} words)")
    log.info("wrote outputs/rejection_log.json, outputs/run_summary.json")
    return {**state, "status": "passed"}


def flag_for_human(state: LessonState) -> LessonState:
    failed = state["verdict"].failed_gates if state.get("verdict") else []
    ids = ", ".join(g.gate_id for g in failed) or "unknown"
    reason = (
        f"Exhausted {state.get('attempt', 0)} generation attempts; "
        f"still failing: {ids}"
    )
    log.node("FLAG_FOR_HUMAN", "retry budget exhausted — escalating")
    log.warn(reason)
    log.info("no lesson was shipped. outputs/rejection_log.json has the full trail.")

    state = {**state, "status": "failed_needs_human", "human_review_reason": reason}
    _write_outputs(state)

    # Failing content never ships -- and a STALE pass must not masquerade as one.
    # An earlier successful run leaves final_lesson.md on disk. If this run
    # escalated and we left that file in place, the outputs directory would
    # still show a shipped lesson, and anything downstream reading the folder
    # would pick up content this run explicitly refused to approve. In a real
    # content pipeline that is precisely how outdated material reaches learners.
    stale = OUTPUT_DIR / "final_lesson.md"
    if stale.exists():
        stale.unlink()
        log.warn("removed a stale final_lesson.md from an earlier run — nothing ships from this one")

    return state


def persist_memory(state: LessonState) -> LessonState:
    """Fold this run's failures into cross-run memory."""
    failures: list[dict[str, str]] = []
    for att in state.get("history", []):
        if att.verdict is None:
            continue
        for g in att.verdict.failed_gates:
            failures.append({"gate_id": g.gate_id, "evidence": g.evidence or ""})

    data = store.record_run(
        topic=state["topic"],
        passed=state.get("status") == "passed",
        attempts=state.get("attempt", 0),
        failures=failures,
    )

    log.node("PERSIST_MEMORY", f"run #{data['total_runs']} recorded")
    if failures:
        counts = data.get("gate_failure_counts", {})
        top = "  ".join(f"{k}×{v}" for k, v in list(counts.items())[:5])
        log.info(f"cumulative gate failures: {top}")
        log.dim("next run's generator prompt will carry these warnings")
    else:
        log.info("no gate failures this run — nothing new to learn")
    return state
