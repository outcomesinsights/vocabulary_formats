# Changelog

Every change to a regex in `vocabulary_formats.tsv`, in date order, with the edge case that
motivated it and the false-negative count measured before and after.

**Why this file exists.** The `notes` column accumulates history that nobody reads in order, and
a later agent re-widens a row that was narrowed for a reason invisible to them. A worked example
from this repo: the `ICD10CM` note said *"Positions 2-3 stay `\w` deliberately — FY2026 introduced
QA0"* while position 2 had **already** been narrowed two weeks earlier. The note defended a state
the row no longer had. A dated log makes that visible; an appended notes field did not.

**The rule these entries serve** (seed `vfm-yr3`): a **false negative is never acceptable** —
a row must never reject a real code judged against its own declared target. A **false positive is
a ratchet** — never widen, tighten one measured increment at a time, and validate at 0 *new* false
negatives against the full concept list before landing.

**Measurement discipline.** Tighten only with (a) the full concept list scored before and after,
and (b) the real corpus tokens that motivated it. Reading a regex is not measuring it.

---

## 2026-08-27 — `ICD10CM`, `ICD10CM.DOTLESS`: position 3 and the `QA` branch

**Edge case.** A human reviewer working through a PMC sleep-apnea paper (`PMC10359192`) was being
offered `T2DM`, `QALY`, `H2O` and `T2D` as candidate ICD-10-CM codes. Ryan asked why, since he
understood ICD-10-CM to be alpha-num-num.

**He was right.** Measured over all 100,035 `ICD10CM` concept_codes:

```
position 1:  A-Z
position 2:  0-9  plus A, O   (only 21 codes break the digit rule: 20 QA*, 1 NO*)
position 3:  0-9  plus A, B   (584 with A — C4A, D3A; 10 with B), plus D in NODX alone
```

Two holes let the junk in: position 3 was `\w`, so `T2DM` matched (T-2-**D**); and the `QA`
branch required no following digit, so `QALY` matched (QA + L + Y) even though every real QA
code is `QA0`.

```
before  ICD10CM          (?:QA|[A-Za-z][0-9])[0-9A-Za-z](\.\w{1,4})?
after   ICD10CM          (?:QA[0-9]|[A-Za-z][0-9][0-9ABab])(\.[0-9A-Za-z]{1,4})?

before  ICD10CM.DOTLESS  (?:QA|[A-Za-z][0-9])[0-9A-Za-z]\w{0,4}
after   ICD10CM.DOTLESS  (?:QA[0-9]|[A-Za-z][0-9][0-9ABab])[0-9A-Za-z]{0,4}
```

**False negatives, against all 100,035 concept_codes:**

| row | before | after |
|---|---|---|
| `ICD10CM` | 1 (`NOD.X`) | 1 (`NOD.X`) |
| `ICD10CM.DOTLESS` | 1 (`NODX`) | 1 (`NODX`) |

`NOD.X` ("No diagnosis", `concept_id` 35209512) is `invalid_reason='D'`, retired 2009-12-31, and
was already a documented deliberate exclusion. **Zero new false negatives.**

**False positives removed:** `T2DM`, `QALY`, `H2O`, `T2D`.

**Still matching, correctly:** `T90` and `P50` — both are *real* ICD-10-CM codes, used in that
paper to mean a saturation measure and a blood-gas value. Shape alone cannot resolve that; it
belongs to context rules or a human. `S13b` also still matches the dotless row (`S13` is real,
`b` falls in the tail).

**Supersedes** the `ICD10CM` note claiming *"positions 2-3 stay `\w` deliberately"*. Position 2
was narrowed 2026-08-12; the FY2026 `QA0` case that motivated permissiveness is now enumerated
explicitly rather than covered by a wildcard.

**Also learned, recorded so it is not repeated:** the 2026-08-13 prose score for
`ICD10CM.DOTLESS` read *"212 tokens, 0 ordinary words"* and did not catch these — because
`T2DM`/`QALY`/`H2O` are **abbreviations**, not dictionary words. The prose check counted the
wrong population.

**Not changed, though it looked worse:** `ICD10PCS`'s default `[0-9A-HJ-NP-Za-hj-np-z]{1,7}`
fullmatches nearly any short word avoiding I and O. Measured in the consumer, it never fires —
it is Tier 2 and no sampled paper names ICD-10-PCS — and `ICD10PCS.BILLABLE` already exists as
the detector-safe sibling. The permissive default is correct for the validator consumer.
