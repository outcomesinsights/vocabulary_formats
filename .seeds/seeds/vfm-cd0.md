---
id: vfm-cd0
title: "Ryan's three questions on Odie's regexes: letters in NDC (yes, 39), SNOMED UUIDs (NOT UK-drug — ALL invalid, so numeric-only has 0 FN on valid codes), and the claims/billable purpose"
status: captured
type: decision
created_at: 2026-07-27T18:38:24.574339+00:00
updated_at: 2026-07-27T18:48:16.401790+00:00
tags:
  - vocabulary-formats
  - ndc
  - snomed
  - claims
  - billable
  - purpose
  - two-consumers
  - odie-review
  - ryan
  - 2026-07-27
converted_at: 2026-09-02T14:41:48.760748+00:00
---

Three questions from Ryan, 2026-07-27, reviewing Odie's regex work. All answered against the
June-2026 Athena build. NOTE a methodology trap hit while answering: **DuckDB's `~` is NOT a regex
match operator** — `SELECT '000199092B0' ~ '[A-Za-z]'` returns FALSE while
`regexp_matches('000199092B0','[A-Za-z]')` returns TRUE. A first pass using `~` reported "0 NDC codes
contain a letter", which was a silent false negative. Use regexp_matches, or scan in Python.

=== Q1: "is a letter ever a valid part of an NDC code?" — YES, but barely ===
**39 of 1,302,950 (0.003%).** Breakdown:
    len=11  class '11-digit NDC'  valid       24
    len=9   class '9-digit NDC'   valid       14
    len=11  class '11-digit NDC'  invalid=D    1
So 38 are VALID concepts, and OHDSI classes them as ordinary 9-/11-digit NDCs despite the letter.
They are radiopharmaceutical kits ("KIT FOR THE PREPARATION OF TECHNETIUM TC 99M..."). They do NOT
all share one labeler prefix.
CONSEQUENCE: NDC.ALPHANUM earns its place, but it covers 39 codes — it is a genuine long tail, not a
significant share. Worth keeping as a variant; not worth loosening the default for.

=== Q2: "are all UUIDs in SNOMED the UK drug extension?" — NO. And the real answer is stronger ===
Odie characterised the 464,018 UUID-shaped SNOMED codes as "retired UK Drug extension". Wrong on the
first half, and it undersells the second.
NOT UK-drug-specific — by concept_class:
    Physical Object      194,791      Qualifier Value    8,735
    Pharma/Biol Product  192,709      Substance          2,786
    Context-dependent     64,755      Model Comp           183
Physical Object is the LARGEST bucket, and Context-dependent / Qualifier Value / Model Comp are not
drugs at all.

**But every single one is INVALID:**
    UUID-shaped (464,018):  invalid_reason='U' 367,198   invalid_reason='D' 96,820   VALID: 0
    numeric IDs (629,129):  VALID+standard 349,211, plus U/D/non-standard
So the UUIDs are not a UK extension — they are **the retired portion of SNOMED, in its entirety**.
Measured directly:
    ^[0-9]+$  vs ALL SNOMED concept_codes      -> 464,018 false negatives
    ^[0-9]+$  vs VALID SNOMED concept_codes    -> **0 false negatives**

**RYAN'S PROPOSAL IS CORRECT AND BETTER-FOUNDED THAN HE PUT IT.** A numeric-only default has ZERO
false negatives against every valid SNOMED concept. Odie's UUID alternation was protecting 464k codes
of which none is valid — and the cost was real: it made the regex accept any UUID as a SNOMED code.
RECOMMEND: default `SNOMED` -> `^[0-9]+$`; keep the UUID form as a variant if a consumer ever needs
retired concepts (name it for what it is — retired/withdrawn — rather than for the UK extension,
which is not what it is).

=== Q3: "primary goal is codes we'd expect in claims data, mostly billable" — YES, and it is the ===
=== repo's NATIVE purpose, not a new one. But it now has a second consumer.                     ===
The framing is already visible in the existing rows: the `.DOTLESS` variants exist because "Medicare
claims data often reports these without the dot". That is a claims-shaped concern. So the claims
target is original, not a reframe.

NDC supports the proposal cleanly:
    len=11  class '11-digit NDC'   953,259     <- the billing form (labeler-product-package)
    len= 9  class '9-digit NDC'    337,085     <- FDA labeler+product, no package segment
    len=11  class 'Device'          11,388
    len= 9  class 'Device'           1,218
OHDSI's own class names draw exactly the distinction Ryan is drawing. So:
    NDC           -> ^\d{11}$              (claims default)
    NDC.COMPLETE  -> ^(\d{9}|\d{11})$      (everything in the vocabulary)
This also fits the repo's established naming: the DEFAULT is the common/expected case and VARIANTS
name the deviation (.DOTLESS, .WITHMODIFIERS, .ALPHANUM). `.COMPLETE` reads correctly as "the whole
vocabulary, not just what you'd see on a claim".

**THE TENSION WORTH NAMING — the repo now serves two consumers with different needs:**
1. CLAIMS canonicalization (the original): billable, claims-observable codes. Ryan's framing.
2. LITERATURE validation (new, via litmine): ANY real code a paper printed, which includes
   non-claims vocabularies. SNOMED barely appears in US claims at all — it is in this repo because
   litmine extracts it from papers, not because it shows up in a claim.
Those pull in opposite directions, and the variant pattern is exactly how to serve both without
choosing: default = claims-shaped, `.COMPLETE`/`.ALPHANUM`/retired-variant = the full vocabulary.
What must NOT happen is the default quietly drifting toward "everything real", which is how the NDC
row ended up rejecting 26% of its own vocabulary while nobody noticed the purpose had blurred.

RECOMMEND stating the two-consumer split explicitly in README.md, because "never reject a real code"
and "codes you'd expect in claims" are different contracts and the repo currently claims only the
first while Ryan intends primarily the second.


## AGREED AND APPLIED (Ryan, 2026-07-27): 'I agree with your conclusions and proposed ideas'
All three answers are now DECISIONS, split into their own seeds:
  vfm-k2n  the claims-default PRINCIPLE (trellis candidate)
  vfm-8l5  NDC — the 338,328-FN bug, default 11-digit, NDC.COMPLETE for 9+11, letters answered
  vfm-27p  SNOMED — UUIDs are entirely retired, numeric-only default, SNOMED.WITHRETIRED variant
Applied to the working tree and validated through the regenerated parquet:
    NDC                vs 11-digit codes (its target)      964,647   FN=25  (all alphanumeric)
    NDC.COMPLETE       vs all NDC concept_codes          1,302,950   FN=39  (all alphanumeric)
    SNOMED             vs VALID SNOMED only                412,033   FN= 0
    SNOMED.WITHRETIRED vs all SNOMED concept_codes       1,093,147   FN= 0
The alphanumeric residuals are NDC.ALPHANUM's job by design, not misses.
README gained the claims-target contract and the scoped false-negative rule.
