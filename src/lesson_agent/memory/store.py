"""Cross-run memory.

The brief asks for memory that "persists across runs; learns from feedback +
logs" and a system that is "self-evolving -- learn from repeated failures to
sharpen prompts/rubrics".

This is deliberately a JSON file rather than a database. It holds a few dozen
lines, it is diffable in a pull request, it can be committed as evidence, and it
can be shown on screen before and after a run. A binary store buys nothing here
and costs a schema, a connection lifecycle, and a "do not commit the db" problem.

What it learns: which gates fail repeatedly, and the actual quoted evidence of
those failures. On the next run that history is injected into the generator
prompt, so the system stops repeating a mistake it has already made twice.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MEMORY_PATH = REPO_ROOT / "memory" / "failure_patterns.json"

# A gate must fail at least this many times before it is worth warning about.
# One failure is noise; a repeat is a pattern.
WARN_THRESHOLD = 2

# Keep the prompt injection small -- the top few offenders only.
MAX_WARNINGS = 4


def _empty() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "total_runs": 0,
        "gate_failure_counts": {},
        "recent_failures": [],
        "last_updated": None,
    }


def load() -> dict[str, Any]:
    if not MEMORY_PATH.exists():
        return _empty()
    try:
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Corrupt memory must never take down a run. Start clean and carry on.
        return _empty()
    base = _empty()
    base.update(data)
    return base


def save(data: dict[str, Any]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    MEMORY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def known_failure_warnings() -> list[str]:
    """Render repeated past failures as instructions for the generator.

    This is the 'self-evolving' edge: the prompt sent on run N is shaped by what
    went wrong on runs 1..N-1.
    """
    data = load()
    counts: Counter[str] = Counter(data.get("gate_failure_counts", {}))
    if not counts:
        return []

    # Most recent quoted example per gate, so the warning is concrete.
    example: dict[str, str] = {}
    for entry in reversed(data.get("recent_failures", [])):
        gid = entry.get("gate_id")
        if gid and gid not in example and entry.get("evidence"):
            example[gid] = entry["evidence"]

    warnings: list[str] = []
    for gate_id, count in counts.most_common(MAX_WARNINGS):
        if count < WARN_THRESHOLD:
            continue
        line = f"{gate_id} has failed {count} times in past runs."
        if gate_id in example:
            snippet = example[gate_id]
            if len(snippet) > 140:
                snippet = snippet[:137] + "..."
            line += f' A previous draft was rejected for: "{snippet}"'
        warnings.append(line)
    return warnings


def memory_block(warnings: list[str] | None = None) -> str:
    """The text spliced into the generator prompt."""
    warnings = known_failure_warnings() if warnings is None else warnings
    if not warnings:
        return ""
    body = "\n".join(f"  - {w}" for w in warnings)
    return (
        "LEARNED FROM PAST RUNS — do not repeat these mistakes:\n"
        f"{body}\n"
        "Pay particular attention to these before you write."
    )


def record_run(
    *,
    topic: str,
    passed: bool,
    attempts: int,
    failures: list[dict[str, str]],
) -> dict[str, Any]:
    """Fold one run's outcome into the persistent record."""
    data = load()
    data["total_runs"] = int(data.get("total_runs", 0)) + 1

    counts = dict(data.get("gate_failure_counts", {}))
    for f in failures:
        gid = f["gate_id"]
        counts[gid] = int(counts.get(gid, 0)) + 1
    data["gate_failure_counts"] = dict(
        sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    )

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    recent = list(data.get("recent_failures", []))
    for f in failures:
        recent.append({
            "run": data["total_runs"],
            "topic": topic,
            "gate_id": f["gate_id"],
            "evidence": f.get("evidence", ""),
            "timestamp": stamp,
        })
    data["recent_failures"] = recent[-40:]  # bounded; this is a memo, not a log

    history = list(data.get("run_history", []))
    history.append({
        "run": data["total_runs"],
        "topic": topic,
        "passed": passed,
        "attempts": attempts,
        "failed_gates": [f["gate_id"] for f in failures],
        "timestamp": stamp,
    })
    data["run_history"] = history[-25:]

    save(data)
    return data
