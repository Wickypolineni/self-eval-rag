# Escalation run — the system refusing to ship

This directory is a real run that **did not produce a lesson**. It is committed
on purpose: a quality gate you have only ever seen say "yes" is not evidence of
a quality gate.

What happened:

```
load_memory  → 2 previous runs on record; 3 repeated failure patterns
               (G1, G4, G6) injected into the generator prompt
attempt 1    → REJECT — failed G1, G2, G3, G4, G6, G7
attempt 2    → REJECT — failed G5 (a factual error, caught against the
               grounding document)
attempt 3    → REJECT — failed G1, G7
router       → ESCALATE — retry budget exhausted
```

Three things worth noting.

**The grounding document did real work.** Attempt 2 was rejected on G5 — a
factual claim contradicting `grounding/rag_reference.md`. An ungrounded judge
would have had only its own recollection to check against.

**Attempt 3 regressed.** It fixed G5 but broke G1 and G7, which had passed on
attempt 2. This is the honest limitation of feedback-driven regeneration: fixing
a targeted failure can disturb something that already worked. It is the main
argument for a small retry budget — more attempts do not converge, they
oscillate.

**Nothing shipped.** `run_summary.json` records `failed_needs_human`, and no
`final_lesson.md` was written. A human is expected to look at this one.
