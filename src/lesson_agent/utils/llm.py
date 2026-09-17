"""The entire provider layer.

OpenRouter is the only provider. One API key reaches every model, so the
generator and the evaluator can be different vendors without a second account.

That vendor split is deliberate and load-bearing: a model grades its own prose
more softly than a stranger's. Google writes the lesson, OpenAI grades it.
Together with the forced-evidence schema in models/evaluation.py, that is two
independent defences against a rubber-stamping judge.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter

load_dotenv()

DEFAULT_GENERATOR = "google/gemini-2.5-flash"
DEFAULT_EVALUATOR = "openai/gpt-5-mini"

# CAREFUL: ChatOpenRouter takes `timeout` in MILLISECONDS, unlike every other
# LangChain chat model, where it is seconds. Passing 180 does not mean three
# minutes -- it means 180ms, so every request times out and the underlying SDK
# then retries with exponential backoff for up to an hour, with no error and no
# output. Verified against langchain-openrouter 0.2.8 / openrouter 0.11.46.
REQUEST_TIMEOUT_MS = 180_000  # 3 minutes


class MissingAPIKey(RuntimeError):
    pass


def _require_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise MissingAPIKey(
            "OPENROUTER_API_KEY is not set.\n"
            "  1. cp .env.example .env\n"
            "  2. paste your key from https://openrouter.ai/settings/keys\n"
        )
    return key


def generator_model() -> ChatOpenRouter:
    """Higher temperature: we want genuinely different prose on a retry."""
    return ChatOpenRouter(
        model=os.getenv("GENERATOR_MODEL", DEFAULT_GENERATOR),
        api_key=_require_key(),
        temperature=0.7,
        max_tokens=8192,
        timeout=REQUEST_TIMEOUT_MS,
        max_retries=2,
        app_title="rag-lesson-evaluator",
    )


def evaluator_model() -> ChatOpenRouter:
    """Temperature 0 and a fixed seed: the same draft should get the same verdict.

    A quality gate that returns a different answer on each run is not a gate.
    """
    return ChatOpenRouter(
        model=os.getenv("EVALUATOR_MODEL", DEFAULT_EVALUATOR),
        api_key=_require_key(),
        temperature=0,
        seed=42,
        max_tokens=8192,
        timeout=REQUEST_TIMEOUT_MS,
        max_retries=2,
        app_title="rag-lesson-evaluator",
    )


def model_names() -> dict[str, str]:
    return {
        "generator": os.getenv("GENERATOR_MODEL", DEFAULT_GENERATOR),
        "evaluator": os.getenv("EVALUATOR_MODEL", DEFAULT_EVALUATOR),
    }
