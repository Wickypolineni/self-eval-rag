"""Console trace.

The graph's behaviour has to be legible while it runs -- both for debugging and
because a reviewer watching a recording needs to see the state transitions, not
a spinner.
"""

from __future__ import annotations

import sys

_BOLD, _DIM, _RESET = "\033[1m", "\033[2m", "\033[0m"
_RED, _GREEN, _YELLOW, _BLUE, _CYAN = (
    "\033[31m", "\033[32m", "\033[33m", "\033[34m", "\033[36m",
)

_WIDTH = 74


def _supports_colour() -> bool:
    return sys.stdout.isatty()


def _c(text: str, colour: str) -> str:
    return f"{colour}{text}{_RESET}" if _supports_colour() else text


def banner(text: str) -> None:
    print()
    print(_c("=" * _WIDTH, _CYAN))
    print(_c(f" {text}", _BOLD + _CYAN))
    print(_c("=" * _WIDTH, _CYAN))


def node(name: str, detail: str = "") -> None:
    arrow = _c("▶", _BLUE)
    label = _c(f"[{name}]", _BOLD)
    print(f"\n{arrow} {label} {_c(detail, _DIM) if detail else ''}")


def info(text: str) -> None:
    print(f"    {text}")


def dim(text: str) -> None:
    print(f"    {_c(text, _DIM)}")


def gate_pass(gate_id: str, name: str) -> None:
    print(f"    {_c('✓', _GREEN)} {_c(gate_id, _GREEN)}  {name}")


def gate_fail(gate_id: str, name: str, evidence: str, fix: str) -> None:
    print(f"    {_c('✗', _RED)} {_c(gate_id, _RED + _BOLD)}  {name}")
    quote = evidence if len(evidence) <= 160 else evidence[:157] + "..."
    print(f"        {_c('quoted:', _DIM)} \"{quote}\"")
    print(f"        {_c('fix:   ', _DIM)} {fix}")


def verdict_line(passed: bool, n_failed: int, total: int) -> None:
    if passed:
        print(f"\n    {_c(f'VERDICT: PASS  ({total}/{total} gates)', _GREEN + _BOLD)}")
    else:
        print(
            f"\n    {_c(f'VERDICT: REJECT  ({n_failed} of {total} gates failed)', _RED + _BOLD)}"
        )


def route(decision: str, reason: str) -> None:
    print(f"\n  {_c('ROUTER →', _YELLOW + _BOLD)} {_c(decision, _BOLD)}  {_c(f'({reason})', _DIM)}")


def warn(text: str) -> None:
    print(f"    {_c('!', _YELLOW)} {text}")


def error(text: str) -> None:
    print(f"    {_c('ERROR', _RED + _BOLD)} {text}")
