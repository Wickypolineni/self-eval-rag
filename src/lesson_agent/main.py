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


def run(topic: str, max_retries: int) -> int:
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
    final = app.invoke(state, {"recursion_limit": 2 * (max_retries + 1) + 6})

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
        "--max-retries",
        type=int,
        default=int(os.getenv("MAX_RETRIES", "2")),
        help="Retries after the first draft (default 2 → 3 generations max).",
    )
    args = p.parse_args()

    try:
        return run(args.topic, args.max_retries)
    except MissingAPIKey as exc:
        log.error(str(exc))
        return 2
    except KeyboardInterrupt:
        log.warn("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(cli())
