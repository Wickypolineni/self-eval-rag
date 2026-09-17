# Architecture

Design decisions and the reasoning behind them. The README covers what the
system does; this covers why it is built this way.

---

## 1. Why a state machine

The task is a loop with a conditional exit: generate, judge, either ship or go
around again, and stop after a bounded number of tries. That is a state machine,
and LangGraph expresses it directly — nodes, edges, and one conditional edge that
carries the routing decision.

The alternative — an agent with tools, free to decide its own next step — was
rejected. For content QA the control flow is the part you least want a model
improvising. A curriculum lead asking "why did this ship?" needs an answer better
than "the agent decided to."

LangGraph is used for orchestration only. LangChain's chain abstractions (LCEL,
agent executors, prompt templates) are deliberately absent: they would wrap the
five nodes that most need to be legible. `ChatOpenRouter` is used purely as a
model client.

## 2. State

```python
class LessonState(TypedDict, total=False):
    topic: str
    audience: str
    lesson: str | None
    verdict: Verdict | None
    attempt: int
    max_retries: int
    history: list[Attempt]        # every draft AND its verdict
    known_failures: list[str]     # loaded from disk, cross-run
    status: RunStatus
    human_review_reason: str | None
```

The load-bearing field is `history`. Keeping every attempt paired with its
verdict — rather than only the latest draft — is what lets retry #2 be smarter
than retry #1. The generator receives the previous draft *and* the specific
quoted reasons it was rejected, never a bare "try again."

It is also what makes the rejection log possible after the fact: *what failed,
why, and what changed on retry* are all reconstructable from `history` at the end
of the run.

## 3. One generate node, not two

A retry is not a different operation from a first draft. It is the same
generation with more context in the prompt. Splitting it into `generate` and
`regenerate` would create:

- two prompt paths that drift apart as one gets tuned and the other does not,
- two edges into `evaluate`,
- two places to forget to inject cross-run memory.

So there is one node. What distinguishes attempt 3 from attempt 1 is the content
of the prompt, not the code that builds it. The branch is four lines:

```python
if is_retry:
    user_prompt = fill(prompts["retry"], previous_lesson=..., feedback=...)
else:
    user_prompt = fill(prompts["first_draft"], ...)
```

## 4. The evaluator

Four properties, in order of how much they matter.

**Grounded.** Gate G5 checks the lesson against `grounding/rag_reference.md`,
which includes an explicit list of false statements about RAG (section 10). The
judge is told that where the lesson and the grounding document disagree, the
lesson is wrong. Without this, factual accuracy reduces to one model's memory of
RAG, which is precisely the failure mode this system exists to catch.

**Forced to cite.** `GateResult` has a model validator that raises if
`passed=False` and `evidence` is empty. A failure without a quote is an opinion,
not a finding.

**Citations verified.** `_quote_appears_in()` checks the quote actually occurs in
the lesson, with fuzzy tolerance for whitespace and case, rejecting matches below
0.75 similarity. A hallucinated citation is discarded and the gate is passed
rather than allowed to drive a retry against a phantom problem.

This fired during the recorded demo. The judge failed G7 citing text absent from
the lesson; the guard caught it. Without the check, the system would have spent a
generation fixing a problem that did not exist.

**Different vendor.** Generator and evaluator are set to different model families
by default. A model grades a stranger's prose more harshly than its own.

### Fail-loud, asymmetrically

Evaluator parse failures are **fatal**: one reparse retry, then raise. An
unreadable verdict must never be treated as a pass, because that would ship
unjudged content — the one outcome the system exists to prevent.

Generator parse failures **degrade gracefully**: fall back to the raw text and
carry on, because the evaluator still judges whatever comes out. You lose the
changelog, not the safety property.

The asymmetry is the point. Fail-loud where a silent failure is dangerous;
degrade where it is merely inconvenient.

The evaluator also rejects an *incomplete* verdict — if the judge omits any gate,
that raises rather than being read as a partial pass.

## 5. The router

```python
def route_after_evaluation(state) -> Literal["retry", "ship", "escalate"]:
    verdict = state.get("verdict")
    if verdict is None:
        raise RuntimeError("router reached with no verdict")
    if verdict.passed:
        return "ship"
    if state["attempt"] < state["max_retries"] + 1:
        return "retry"
    return "escalate"
```

This is the assessment. It is the point where the system decides, autonomously,
whether content is good enough for a learner.

It contains no LLM call. It reads one boolean and compares two integers.

Three outcomes, and the third is what makes the autonomy safe. A two-outcome
router — ship or retry — either ships failing content once the budget runs out or
loops forever. `flag_for_human` is a legitimate terminal state: the system
recording that it could not meet the bar and that a person should look.

`test_failing_content_never_ships` pins the safety property directly: at every
attempt count, a failed verdict never routes to `ship`.

## 6. Memory and self-evolution

Two levels of feedback:

**Within a run** (`history` → retry prompt): specific, quoted, immediate.

**Across runs** (`failure_patterns.json` → generator prompt): aggregated. Once a
gate has failed twice, the next run's generator is warned before it writes a
word, with a real quote from a past rejection.

The threshold matters. One failure is noise — a single bad draft. Two is a
pattern worth pre-empting. Warnings are capped at four so the prompt does not
bloat, and `recent_failures` is bounded at 40 entries: this is a memo, not a log.

Both terminal paths route through `persist_memory`. A failed run teaches the
system more than a passing one, so memory must not be skipped on escalation.

## 7. What a run looks like

```
load_memory     → 0 previous runs, no patterns yet
generate #1     → 539 words (sabotaged prompt)
evaluate #1     → G1 ✗ G2 ✗ G3 ✗ G4 ✗ G5 ✓ G6 ✗ G7 ✓  → REJECT
                  (G7 citation unverifiable → discarded)
router          → REGENERATE (2 attempts left)
generate #2     → 974 words, addressing G1 G2 G3 G4 G6
evaluate #2     → 7/7 ✓ → PASS
router          → SHIP
finalize        → final_lesson.md, rejection_log.json, run_summary.json
persist_memory  → run #1 recorded; G1,G2,G3,G4,G6 each +1
```

## 8. Known limitations

**The evaluator is unmeasured.** I can demonstrate it catching a deliberate
error. I cannot yet state how often it misses one. Closing that needs a held-out
set of lessons with planted errors and a precision/recall number on the judge
itself. This is the most important missing piece, and I would build it first.

**Gate independence is assumed.** G1 (jargon) and G6 (accessibility) overlap
heavily; they frequently fail together, which slightly overweights language
problems relative to, say, factual accuracy. Acceptable for one topic, worth
revisiting across a curriculum.

**One grounding document, one topic.** Scaling to arbitrary topics needs a
grounding document per topic, which becomes a retrieval problem itself — and at
that point the accuracy gate is doing real RAG rather than reading one file.

**Advisory scores are recorded but unused.** They feed nothing yet beyond the
logs. The obvious next step is using a persistent low score in a dimension to
sharpen the relevant section of the generator prompt — the "sharpen prompts and
rubrics" half of the brief's self-evolving requirement, which is currently served
only at the gate level.
