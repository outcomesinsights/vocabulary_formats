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

______________________________________________________________________

## 2026-10-31 — every row is case-exact (`vocabulary_formats-7a1`)

**Edge case.** In a conceptql session Ryan ruled that `i16.5` must not pass as an ICD-10-CM code:
"if a code should be case insensitive, the vocabulary_format regexp should explicitly list case
insensitivity. call me a stickler, but I think ICD-10-CM code i16.5 just doesn't look right and
shouldn't be repected" (seed `vfm-8k1`). Before this change, 23 rows admitted lower case through
`[A-Za-z]`, `[a-z]` or `\w`. So `i16.5` passed `ICD10CM`, and `ICD10PCS` accepted `0dtj0zz` while
its own `.BILLABLE` variant did not.

**The rule now.** A row is case-exact. A row that is case-insensitive declares it with the scoped
flag `(?i:...)`. `just lint` refuses a global flag such as `(?i)` and every other inline flag. No
row declares `(?i:...)`: the Athena census (release 20260625) found no lower-case code in any
vocabulary with a row, except the SNOMED UUIDs and three NDC codes.

**The change.** Every `\w` and every lower-case range became an explicit class: `[0-9A-Z]` for
`\w`, and the upper-case half of each letter range. `SNOMED.WITHRETIRED` went the other way, to
lower-case hex `[0-9a-f]`, because all 464,018 published UUIDs are lower-case hex. Rows changed:
`ICD10CM`, `ICD10CM.DOTLESS`, `ICD10`, `ICD10.DOTLESS`, `ICD10PCS`, `HCPCS`,
`HCPCS.WITHMODIFIERS`, `HCPCS_MODIFIER`, `CPT4`, `CPT4.WITHMODIFIERS`, `CPT4_MODIFIER`,
`CPT4_HCPCS`, `CPT4_HCPCS.WITHMODIFIERS`, `CPT4_HCPCS.CODEONLY`, `CPT4_HCPCS_MODIFIER`,
`NDC.ALPHANUM`, `ATC`, `SNOMED.WITHRETIRED`, `ICDO3`, `ICDO3.CODEONLY`, `ICD03_Topography`,
`ICD03_Topography.DOTLESS`, `EDI`. Each row's `notes` carries its old pattern and its numbers.

**False negatives.** `just test` before and after: 38 of 38 rows, 9,798,861 codes, **0 false
negatives**. One exclusion was added first, on 2026-10-31: the three lower-case NDC codes
`1549912340a`, `1549912340b` and `5812800010a` are excluded from `NDC.ALPHANUM`'s target, for case
only (seed `vfm-5g7`). Their letters are respected, and `1549912340A` passes.

**False positives removed** (`just prose`, FY2026 tabular, 21,259 tokens; the paper corpus was not
on this machine):

| row                                                         | tokens         | ordinary words |
| ----------------------------------------------------------- | -------------- | -------------- |
| `ICD10PCS`                                                  | 3,795 → 1,696  | 2,325 → 258    |
| the three modifier rows and the three `.WITHMODIFIERS` rows | 244–245 → 168  | 111 → 42       |
| `CPT4`, `CPT4_HCPCS`, `EDI`                                 | 1 → 0          | 0 → 0          |
| `ATC`                                                       | 744 → 730      | 27 → 13        |
| `ICD10CM`, `ICD10`, `ICD10.DOTLESS`, `ICD10CM.DOTLESS`      | 4–5 fewer each | unchanged      |

The ICD rows lost `M5a`, `M5b`, `q11`, `q34` and `p110d`: chromosome bands, a gene product and
leukaemia subtypes, none of them codes. `ATC` lost the 14 single lower-case letters.

**Supersedes** the `ICD10PCS` note "Case stays permissive on purpose", and the 2026-08-27 entry's
paragraph "Not changed, though it looked worse". The note predicted that the upper-case pattern
would cut the tabular figure to 1,695. The measured figure is 1,696, on a corpus 11 tokens larger.

**For consumers.** Do not compile a row with an ignore-case flag. It overrides the row. If a
source writes codes in lower case, change the case in a named step before validation. See the
README section *The patterns are case-exact*.

______________________________________________________________________

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

| row               | before      | after       |
| ----------------- | ----------- | ----------- |
| `ICD10CM`         | 1 (`NOD.X`) | 1 (`NOD.X`) |
| `ICD10CM.DOTLESS` | 1 (`NODX`)  | 1 (`NODX`)  |

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
