---
id: vfm-k2n
title: "PRINCIPLE: the default regex targets CLAIMS-OBSERVABLE codes; variants carry the full vocabulary — the repo has two consumers and the default must not drift toward 'everything real'"
status: captured
type: decision
created_at: 2026-07-27T18:45:36.677158+00:00
updated_at: 2026-07-27T18:45:36.677166+00:00
tags:
  - principle
  - purpose
  - claims
  - billable
  - two-consumers
  - variants
  - contract
  - ryan
  - 2026-07-27
  - trellis-candidate
converted_at: 2026-09-02T14:41:48.760748+00:00
---

DECIDED (Ryan, 2026-07-27): 'my primary goal for vocabulary_formats is to find codes we'd expect to
see in claims data so, mostly billable.'

## The principle

For each vocabulary, the DEFAULT row targets what you would expect to see in CLAIMS DATA. Anything
broader — the full vocabulary, retired concepts, alternate encodings — goes in a NAMED VARIANT.

This is not a new direction. It is already visible in the oldest rows: the `.DOTLESS` variants exist
because 'Medicare claims data often reports these without the dot'. The claims target is native to
the repo; it had simply never been written down, and the default drifted without anyone noticing.

## Why it needs stating — the repo now has TWO consumers pulling opposite ways

1. **Claims canonicalization** (original): billable, claims-observable codes. Producers canonicalize
   codes harvested from claims-shaped sources before the catalog's exact join.
2. **Literature validation** (new, via litmine): ANY real code a paper printed, including
   non-claims vocabularies. SNOMED is in this repo because litmine extracts it from PAPERS, not
   because it appears on a US claim.
   The variant pattern serves both without choosing. The failure mode is the DEFAULT quietly widening to
   mean 'everything real' — which is exactly how the NDC row came to reject 26% of its own vocabulary
   while nobody noticed the purpose had blurred (see the NDC sibling seed).

## How this interacts with 'never reject a real code'

It does NOT overturn it; it scopes it. Within a row's stated target, false negatives remain
unacceptable — the ICD10CM regression (1,953 real 3-char codes rejected) and the NDC one (338,328)
are still bugs, because both rejected codes squarely inside the row's own target.
What changes: the TARGET is now explicit per row, so 'is this a false negative?' has an answerable
scope. A 9-digit NDC failing the claims-default `NDC` row is CORRECT; failing `NDC.COMPLETE` is a bug.

## Consequence for README.md

The README currently claims only 'never reject a real code'. That is the second consumer's contract.
State both: the default is claims-shaped, variants carry the rest, and false negatives are judged
against the row's declared target. Without that, the next agent widening a default is doing the
reasonable thing under the documented contract.

## TRELLIS CANDIDATE

This is a durable, always-on rule for the repo — it governs every future row. Worth promoting into
vocabulary_formats' CLAUDE.md once the wording settles.
