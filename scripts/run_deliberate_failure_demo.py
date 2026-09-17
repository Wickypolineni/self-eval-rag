#!/usr/bin/env python
"""Deliberate-failure demo — the evaluator catching a real error.

The assessment requires showing "your evaluator catching a deliberate error".
A system that passes on the first attempt every time proves nothing: you cannot
tell a working quality gate from a gate that says yes to everything.

So this script sabotages the FIRST draft only. It swaps the generator's system
prompt for one that instructs a jargon-heavy, professor-to-postgraduate register
-- exactly the register the rubric is built to reject. After that first draft,
the normal prompt is restored, so the retry is a genuine repair rather than a
second sabotage.

Nothing in src/ is modified. The sabotage is a patch applied here and confined
to this script, so what you watch is the real pipeline, judged by the real
rubric, with one bad input deliberately fed in.

    Expected sequence:
      attempt 1  → jargon-dense draft  → evaluator REJECTS (expect G1 / G6)
                                         with verbatim quotes as evidence
      attempt 2  → repaired draft      → evaluator PASSES
      memory     → the failed gates are recorded for future runs
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

from lesson_agent.main import DEFAULT_TOPIC  # noqa: E402
from lesson_agent.nodes import generate as generate_node  # noqa: E402
from lesson_agent.utils import config, logging as log  # noqa: E402

SABOTAGED_SYSTEM = """
You are a distinguished professor writing for a graduate seminar in machine learning.

Write with full technical density and academic register. Use the field's
vocabulary freely and without definition -- your audience are specialists.
Terms such as dense vector representation, latent semantic space, corpus,
approximate nearest neighbour search, cosine similarity, embedding dimensionality,
inference-time conditioning, parametric knowledge and non-parametric memory should
appear naturally and without explanation.

Favour long, complex, multi-clause sentences. Use idiomatic English freely.
Do not include worked examples -- they dilute rigour at this level.

Write the lesson in Markdown. Output only the lesson.
"""


def main() -> int:
    load_dotenv()

    log.banner("DELIBERATE FAILURE DEMO")
    log.info("The first draft is sabotaged on purpose: a jargon-heavy prompt that")
    log.info("the rubric is designed to reject. Everything after it is the real system.")
    log.info("")
    log.info("Watch for: the evaluator quoting the exact offending text,")
    log.info("then the retry repairing those specific failures.")

    real_prompts = config.load_prompts()
    sabotaged = copy.deepcopy(real_prompts)
    sabotaged["generator"]["system"] = SABOTAGED_SYSTEM

    calls = {"n": 0}

    def patched_load_prompts() -> dict:
        """Sabotage attempt 1 only; every later attempt gets the real prompt."""
        calls["n"] += 1
        if calls["n"] == 1:
            log.warn("SABOTAGE ACTIVE — attempt 1 uses the jargon-heavy prompt")
            return sabotaged
        return real_prompts

    # Patch the name as generate.py resolved it. src/ is untouched.
    generate_node.load_prompts = patched_load_prompts

    from lesson_agent.main import run  # noqa: E402  (import after patching)

    return run(DEFAULT_TOPIC, max_retries=2)


if __name__ == "__main__":
    sys.exit(main())
