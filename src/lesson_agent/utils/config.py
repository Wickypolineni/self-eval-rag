"""Loaders for the YAML config and the grounding document."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACKAGE_ROOT.parent.parent
CONFIG_DIR = REPO_ROOT / "configs"


@functools.lru_cache(maxsize=None)
def load_rubric() -> dict[str, Any]:
    return yaml.safe_load((CONFIG_DIR / "rubric.yaml").read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def load_prompts() -> dict[str, Any]:
    return yaml.safe_load((CONFIG_DIR / "prompts.yaml").read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def load_grounding() -> str:
    return (PACKAGE_ROOT / "grounding" / "rag_reference.md").read_text(encoding="utf-8")


def audience_description() -> str:
    return load_rubric()["audience"]["description"].strip()


def gate_ids() -> list[str]:
    return [g["id"] for g in load_rubric()["gates"]]


def advisory_ids() -> list[str]:
    return [s["id"] for s in load_rubric()["advisory_scores"]]


def render_rubric_for_prompt() -> str:
    """Flatten the gates into prompt text, so the judge sees exactly the
    criteria the repo documents. One source of truth, no drift."""
    rubric = load_rubric()
    out: list[str] = []
    for g in rubric["gates"]:
        out.append(f"--- {g['id']}: {g['name']} ---")
        out.append(f"CHECK: {g['check'].strip()}")
        out.append(f"FAILS WHEN: {g['fails_when'].strip()}")
        out.append("")
    out.append("ADVISORY DIMENSIONS (1-5, diagnostics only, never affect pass/fail):")
    for s in rubric["advisory_scores"]:
        out.append(f"  - {s['id']}: {s['description']}")
    return "\n".join(out)
