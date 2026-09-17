"""Template filling by token replacement, not str.format().

Lesson content contains Markdown, code fences, and JSON -- all of which carry
literal braces. str.format() would raise KeyError or silently mangle them, so
templates are filled by plain replacement of {named} tokens instead.
"""

from __future__ import annotations


def fill(template: str, **values: str) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{" + key + "}", value if value is not None else "")
    return out


def strip_code_fences(text: str) -> str:
    """Remove a wrapping ```json ... ``` fence if a model added one."""
    t = text.strip()
    if not t.startswith("```"):
        return t
    lines = t.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
