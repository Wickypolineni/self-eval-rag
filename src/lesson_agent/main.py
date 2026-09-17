"""CLI entrypoint."""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from lesson_agent.graph import build_graph
from lesson_agent.state import initial_state
from lesson_agent.utils import logging as log
from lesson_agent.utils.config import audience_description, gate_ids
from lesson_agent.utils.llm import MissingAPIKey, model_names

DEFAULT_TOPIC = "Introduction to RAG (Retrieval-Augmented Generation)"


def _pause(node_name: str, state: dict) -> None:
    """Hold between nodes so the graph can be inspected while it runs."""
    attempt = state.get("attempt", 0)
    status = state.get("status", "?")
    verdict = state.get("verdict")

    log.dim("─" * 66)
    log.info(f"paused after [{node_name}]")
    log.dim(f"  attempt={attempt}  status={status}  history={len(state.get('history', []))} draft(s)")
    if verdict is not None:
        failed = [g.gate_id for g in verdict.failed_gates]
        log.dim(f"  verdict: {'PASS' if verdict.passed else 'REJECT'}"
                + (f"  failing {', '.join(failed)}" if failed else ""))
    if state.get("known_failures"):
        log.dim(f"  memory: {len(state['known_failures'])} pattern(s) in the prompt")

    try:
        reply = input("  [Enter] continue · [s] show current draft · [q] quit > ").strip().lower()
    except EOFError:
        return
    if reply == "q":
        raise KeyboardInterrupt
    if reply == "s" and state.get("lesson"):
        print()
        print(state["lesson"][:2500])
        print()
        try:
            input("  [Enter] continue > ")
        except EOFError:
            return


def run(topic: str, max_retries: int, step: bool = False) -> int:
    load_dotenv()
    models = model_names()

    log.banner("SELF-EVALUATING LESSON GENERATOR")
    log.info(f"topic      : {topic}")
    log.info(f"generator  : {models['generator']}")
    log.info(f"evaluator  : {models['evaluator']}   (different vendor — on purpose)")
    log.info(f"gates      : {', '.join(gate_ids())}  (all binary, no partial credit)")
    log.info(f"budget     : {max_retries} retries → {max_retries + 1} generations maximum")

    app = build_graph()
    state = initial_state(
        topic=topic,
        audience=audience_description(),
        max_retries=max_retries,
    )

    # recursion_limit is a backstop: the retry cap in the router is the real
    # termination guarantee, but a graph that could loop forever is a bug even
    # if the logic says otherwise.
    config = {"recursion_limit": 2 * (max_retries + 1) + 6}

    if not step:
        final = app.invoke(state, config)
    else:
        # Stream node by node so the graph can be watched and paused. Same
        # graph, same nodes -- stream() just surfaces each transition instead
        # of returning only the end state.
        log.warn("step mode: pausing after every node")
        final = state
        for chunk in app.stream(state, config, stream_mode="updates"):
            for node_name, update in chunk.items():
                if isinstance(update, dict):
                    final = {**final, **update}
                _pause(node_name, final)

    log.banner("RUN COMPLETE")
    status = final.get("status")
    if status == "passed":
        log.info(f"SHIPPED after {final['attempt']} generation(s) → outputs/final_lesson.md")
        return 0
    log.info(f"NOT SHIPPED — {final.get('human_review_reason')}")
    log.info("see outputs/rejection_log.json")
    return 1


def cli() -> int:
    p = argparse.ArgumentParser(
        prog="lesson-agent",
        description="Generate a beginner lesson, judge it against binary quality gates, "
                    "and regenerate until it clears the bar or escalate to a human.",
    )
    p.add_argument("--topic", default=DEFAULT_TOPIC, help="Lesson topic.")
    p.add_argument(
        "--step",
        action="store_true",
        help="Pause after each node so you can inspect the state as it runs.",
    )
    p.add_argument(
        "--max-retries",
        type=int,
        default=int(os.getenv("MAX_RETRIES", "2")),
        help="Retries after the first draft (default 2 → 3 generations max).",
    )
    args = p.parse_args()

    try:
        return run(args.topic, args.max_retries, step=args.step)
    except MissingAPIKey as exc:
        log.error(str(exc))
        return 2
    except KeyboardInterrupt:
        log.warn("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(cli())
