---
id: vfm-yop
title: ICD10PCS default should require exactly 7 characters; hierarchy nodes move to ICD10PCS.COMPLETE
status: captured
type: decision
created_at: 2026-08-17T22:35:34.171988+00:00
updated_at: 2026-08-17T22:37:25.400515+00:00
tags:
  - icd10pcs
  - narrowing
  - claims-observable
  - collision
  - drg
  - rxnorm
  - variant
  - rule-k2n
  - 2026-08-17
converted_at: 2026-09-02T14:41:48.760748+00:00
---

The row is `[0-9A-HJ-NP-Za-hj-np-z]{1,7}` and its own notes already call it "the LOOSEST row in
the table", one that "cannot carry its own weight in a text scan" — 2,323 ordinary English words
survive it. The `{1,7}` is there because 1-6 character codes are real hierarchy/partial-code
concepts.

MEASURED 2026-08-17 against Athena 20260625 CONCEPT (10,281,915 distinct
(vocabulary_id, concept_code) across 131 vocabularies):

  ICD10PCS length distribution
    1ch 17 | 2ch 115 | 3ch 918 | 4ch 12,049 | 5ch 34,590 | 6ch 67,079 | 7ch 82,327 | 10ch 3
    (the 10ch are the MTHU* UMLS GEM nodes, already excluded by the target)
    -> 82,327 billable codes vs 114,768 hierarchy nodes (+3 excluded MTHU)

  DRG (871) n ICD10PCS (197,098) = 52 shared code strings — ALL 52 are 3 characters
  Requiring exactly 7 characters:
    DRG    n ICD10PCS(7) = 0 shared strings
    RxNorm n ICD10PCS(7) = 0 shared strings  (was 3)

So the ENTIRE cross-vocabulary collision between ICD10PCS and both DRG and RxNorm is carried by
the partial hierarchy nodes, and a length constraint removes it completely — no alphabet change,
no new artifact, no release pin, no size cost.

This is what [[vfm-k2n]] already asks for: the default targets CLAIMS-OBSERVABLE codes and
variants carry the full vocabulary. A hierarchy node is not claims-observable. Today's default is
arguably a standing violation of that principle rather than a new narrowing.

PROPOSED
  ICD10PCS           [0-9A-HJ-NP-Za-hj-np-z]{7}      (billable form — the default)
  ICD10PCS.COMPLETE  [0-9A-HJ-NP-Za-hj-np-z]{1,7}    (today's pattern, unchanged)

Naming follows NDC's precedent — `NDC` is the 11-digit claims form and `NDC.COMPLETE` is the 9+11
full vocabulary, the same default-vs-whole-vocabulary split. The alternative is `.WITHHIERARCHY`
on the `SNOMED.WITHRETIRED` pattern. That is the one open call in this seed.

COST — two files, not one. `checks/validation_targets.json` must gain a `code_filter` of
exactly-7 on the ICD10PCS target plus a new entry for the variant; without it `just test` fails
with 114,768 in-target false negatives, because the declared target is still the whole vocabulary.

NOT MEASURED: this should also improve the prose false-positive figures the row scores worst on —
7-character i/o-free words are far rarer than 1-7 character ones — but that has not been run.
Score it with `just prose --try` before and after; do not assume the direction.

Case stays permissive. The existing note is right that `[0-9A-HJ-NP-Z]` would hand a
lowercase-normalizing caller a silent 100% false-negative rate. This seed changes length only.

Evidence: claude_stuff/code-collision-20260817-151740.log
          claude_stuff/pcs-length-20260817-151904.log
