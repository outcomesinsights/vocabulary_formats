---
id: vfm-v3k
title: "Committed edge-case fixtures: known-good as a hard gate, known-bad as a burn-down that can only shrink"
status: captured
type: idea
created_at: 2026-08-27T20:56:05.528959+00:00
updated_at: 2026-08-27T20:56:05.528959+00:00
tags:
  - fixtures
  - testing
  - ratchet
  - gate
  - ryan
  - 2026-08-27
converted_at: 2026-09-02T14:41:48.760748+00:00
---

RYAN, 2026-08-27:

  "I wonder if vocabulary_formats needs to keep a collection of known good, known positive edge
   cases, and known negative edge cases. I am tempted almost to have a testing framework put in
   that would run each regular expression through a set of known good cases just to verify that
   we never drift into false negative territory, but then also maintains a set of things that
   have historically been false positives that we would like to tighten against."

Yes. It is the executable form of the ratchet in vfm-yr3, and it fills a real gap rather than
duplicating what is here.

## WHAT ALREADY EXISTS, so this does not reinvent it

  checks/false_negatives.py  (just test)   every row vs its declared target, pulled LIVE from the
                                           OHDSI substrate. The completeness half.
  checks/prose.py            (just prose)  every row vs ordinary English. Explicitly "A REPORT,
                                           NOT A GATE" -- no threshold, and rightly so.

## THE TWO GAPS

1. `just test` needs a ~1.4 GB Athena download and SKIPS CLEANLY without one. So on a machine
   with no substrate there is NO false-negative guard whatsoever -- and `just lint`, the thing
   that always runs, does not check codes at all. A small COMMITTED known-good set closes that:
   it gates on every machine, in seconds, with no database.

2. There is NO record of specific historical false positives. prose.py scores prose generically
   but remembers nothing, so nothing prevents a future widening from re-admitting T2DM, QALY,
   H2O or T2D. The tightening that removed them on 2026-08-27 is protected by exactly nothing.

## THE DESIGN, and the asymmetry is the point

known-good        must match. HARD GATE. A failure is a false negative, which vfm-yr3 makes
                  inviolable. Small and hand-picked: the structural edges, not a sample --
                  C4A and D3A (letter in position 3), QA0 (letter in position 2), I10 (bare
                  3-char category), E11.9, V45.81, NDC 9- and 11-digit forms, and every code
                  a past regression actually rejected.

known-bad         must NOT match, in TWO STATES:

                    rejected      the row does not match it and never may again.
                                  HARD GATE. Regression protection.
                    still-matching  the row DOES match it. Recorded as KNOWN DEBT.
                                  NOT a failure.

                  An entry may move still-matching -> rejected. It must NEVER move back. That
                  one-way constraint IS the ratchet, made executable.

This shape already exists in the sibling literature repo as an xfail burn-down (17 flattening
sites in 11 modules, with the marker asserting that an XPASS means the work is done). Same idea:
the debt is enumerated, visible, and can only decrease.

## WHY still-matching MUST NOT FAIL THE BUILD

Because some of it is not fixable and pretending otherwise breaks rule 1. T90 and P50 are REAL
ICD-10-CM codes that this literature corpus uses to mean a saturation measure and a blood-gas
value. No regex can reject them without rejecting real codes. They belong in known-bad as
permanently still-matching, annotated -- the honest record that shape alone cannot decide them,
and that the decision belongs to context rules or a human. A gate that failed on those would
push someone to break rule 1 to get green.

## Format sketch, data not code

Per row: vocabulary_id, the token, the state, where it was found (a real PMC id or concept
source), and one line of why. Harvested from real documents, never invented -- the standing rule
in the literature consumer is clc-ass, and the same discipline applies here.

## PRE-EXISTING BLOCKER, must be fixed first

`just lint` is currently RED at HEAD for reasons unrelated to any data: it reports all 35
validation targets as orphans -- ATC, CPT4, SNOMED, ICD10CM, everything -- so its row-lookup is
broken, not the TSV (39 rows, 6 fields, all present and correct). Measured 2026-08-27: 35
violations before my ICD10CM change and 35 after. A repo whose gate is already red cannot adopt
a new gate; nobody will be able to tell the new failures from the standing ones.
