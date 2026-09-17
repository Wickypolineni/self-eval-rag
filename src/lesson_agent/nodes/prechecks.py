"""Deterministic gate checks that run BEFORE the LLM judge.

Why this exists: during development the LLM evaluator passed a deliberately
sabotaged draft -- dense academic prose, 60-word sentences, "non-parametric
memory", "latent semantic space" -- on both G1 (no unexplained jargon) and G6
(readable by a limited-English learner). Its own advisory scores on that same
draft were 1 and 2 out of 5, so the judge could see the content was bad and
still would not commit to a binary fail.

That is a false negative in a quality gate, which is worse than no gate: it
ships bad content while reporting that it checked.

The response is not a better prompt. Some of what these gates measure is not a
matter of judgement at all. Sentence length is arithmetic. Whether the string
"latent semantic space" appears in a lesson for a beginner is a lookup. Those
are computed here, for free, deterministically, and they cannot be talked out of
a failure.

The LLM judge still runs and still owns the gates that genuinely need reading
comprehension. A precheck failure simply overrides a pass on that gate --
defence in depth, cheapest and most reliable layer first.
"""

from __future__ import annotations

import re

from lesson_agent.models.evaluation import GateResult

# A beginner lesson should not contain these at all. They are not terms that
# need a careful definition -- for this reader they are the wrong register
# entirely, and their presence means the draft was written for someone else.
DISQUALIFYING_JARGON = [
    "non-parametric", "parametric knowledge", "parametric memory",
    "latent semantic", "latent space", "dense vector representation",
    "high-dimensional", "lower-dimensional", "dimensionality",
    "approximate nearest neighbour", "approximate nearest neighbor",
    "cosine similarity", "vector space", "embedding space",
    "inference-time", "architectural paradigm", "semantic similarity",
    "transformer-based", "encoder", "corpus", "corpora",
]

# Idioms and figures of speech. The reader learned English as a second or third
# language; these do not translate.
IDIOMS = [
    "piece of cake", "under the hood", "boils down to", "rule of thumb",
    "in a nutshell", "the bottom line", "at the end of the day",
    "bread and butter", "rocket science", "wrap your head around",
    "rubber meets the road", "hit the ground running", "the lion's share",
    "ballpark", "no-brainer", "silver bullet", "cut to the chase",
]

# A 12th-grade reader with limited English loses the thread in long sentences.
MAX_SENTENCE_WORDS = 35
MAX_MEAN_SENTENCE_WORDS = 25


def _sentences(text: str) -> list[str]:
    """Split prose into sentences, ignoring code blocks, headings and lists."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    lines = [
        ln for ln in text.splitlines()
        if not ln.strip().startswith(("#", "|", ">", "*", "-", "1.", "2.", "3."))
    ]
    prose = " ".join(lines)
    parts = re.split(r"(?<=[.!?])\s+", prose)
    return [p.strip() for p in parts if len(p.split()) > 2]


def _check_sentence_length(lesson: str) -> GateResult | None:
    sentences = _sentences(lesson)
    if not sentences:
        return None

    lengths = [len(s.split()) for s in sentences]
    longest = max(lengths)
    mean = sum(lengths) / len(lengths)

    if longest <= MAX_SENTENCE_WORDS and mean <= MAX_MEAN_SENTENCE_WORDS:
        return None

    worst = sentences[lengths.index(longest)]
    return GateResult(
        gate_id="G6",
        passed=False,
        reasoning=(
            f"Sentences are too long for this reader: longest is {longest} words "
            f"(limit {MAX_SENTENCE_WORDS}), mean is {mean:.1f} "
            f"(limit {MAX_MEAN_SENTENCE_WORDS}). Measured, not judged."
        ),
        evidence=worst[:400],
        fix_instruction=(
            f"Break long sentences up. No sentence over {MAX_SENTENCE_WORDS} words, "
            f"and keep the average under {MAX_MEAN_SENTENCE_WORDS}. One idea per sentence."
        ),
    )


def _check_disqualifying_jargon(lesson: str) -> GateResult | None:
    low = lesson.lower()
    found = [t for t in DISQUALIFYING_JARGON if t in low]
    if not found:
        return None

    term = found[0]
    idx = low.index(term)
    quote = lesson[max(0, idx - 90): idx + 110].strip()
    return GateResult(
        gate_id="G1",
        passed=False,
        reasoning=(
            f"Contains graduate-level terminology unsuitable for an absolute "
            f"beginner: {', '.join(found[:6])}. Found by lookup, not judgement."
        ),
        evidence=quote,
        fix_instruction=(
            f"Remove or replace these terms entirely: {', '.join(found[:6])}. "
            "Use everyday words. For example say 'a list of numbers that captures "
            "meaning' rather than 'dense vector representation'."
        ),
    )


def _check_idioms(lesson: str) -> GateResult | None:
    low = lesson.lower()
    found = [i for i in IDIOMS if i in low]
    if not found:
        return None

    idx = low.index(found[0])
    return GateResult(
        gate_id="G6",
        passed=False,
        reasoning=(
            f"Uses English idioms a non-English-medium reader will not know: "
            f"{', '.join(found[:4])}."
        ),
        evidence=lesson[max(0, idx - 80): idx + 100].strip(),
        fix_instruction=(
            f"Remove these idioms and say the plain meaning instead: {', '.join(found[:4])}."
        ),
    )


def run_prechecks(lesson: str) -> list[GateResult]:
    """Deterministic failures. Empty list means nothing objective was wrong."""
    results: list[GateResult] = []
    for check in (_check_disqualifying_jargon, _check_sentence_length, _check_idioms):
        if (failure := check(lesson)) is not None:
            results.append(failure)

    # One failure per gate; the first is the most severe.
    seen: set[str] = set()
    deduped: list[GateResult] = []
    for r in results:
        if r.gate_id not in seen:
            seen.add(r.gate_id)
            deduped.append(r)
    return deduped
