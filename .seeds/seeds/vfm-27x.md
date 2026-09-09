---
id: vfm-27x
title: "REJECTED on measurement: a condensed 'legitimate code paths' regex for ICD10PCS buys 2x — the constraint is in the position dependencies, not the alphabets"
status: captured
type: exploration
created_at: 2026-08-17T22:35:50.506243+00:00
updated_at: 2026-08-17T22:39:11.818926+00:00
tags:
  - icd10pcs
  - grammar
  - condensation
  - trie
  - enumeration
  - rejected
  - measured
  - membership
  - litmine
  - 2026-08-17
converted_at: 2026-09-02T14:41:48.760748+00:00
---

THE NOTION (Ryan, 2026-08-17): not an enumerating regex, but a complex regex condensed down so it
matches all real codes by following all legitimate code paths. For ICD10PCS this is well
motivated — CMS defines PCS exactly that way, as a positional 7-axis system where each axis draws
from a restricted set.

MEASURED over the 82,327 billable 7-character codes (Athena 20260625). All three are scored at
exactly 7 characters so they are comparable; the SHIPPED row is the case-permissive {1,7} form,
which is looser than line A:

```
  A. one alphabet      [0-9A-HJ-NP-Z]{7}          accepts 52,523,350,144   637,985x over-permissive
  B. per-position      102 bytes                  accepts 24,716,870,656   300,228x over-permissive
  C. all legit paths   377,446 bytes (trie)       accepts exactly 82,327        1x
```

distinct values per position: [17, 34, 34, 34, 32, 34, 34]

PER-POSITION CONDENSATION BUYS A FACTOR OF 2. Only position 1 (section, 17 values) and position 5
(32) narrow at all; positions 2, 3, 4, 6 and 7 each use essentially the entire 34-character
alphabet. ICD10PCS's structure lives almost entirely in the DEPENDENCIES BETWEEN POSITIONS —
which body-part values are legal depends on the operation, which depends on the body system,
which depends on the section. A regex constraining each position independently captures almost
none of the real constraint.

CONCLUSION — there is no useful middle. Condensing "all legitimate paths" as far as prefix
factoring goes IS the trie: 377 KB, 57% of raw alternation. The condensed grammar and the
enumeration are the same object, and 377 KB would put a release pin on a repo that deliberately
has none. Rejected on the measurement, not on taste.

CAVEAT ON THE MEASUREMENT: the trie was built from the code list, not from CMS's ~2,000 PCS Table
rows, which are a genuinely more compact generative grammar — plausibly 50-150 KB as a regex.
Better, same order of magnitude, still a release snapshot. Worth knowing that parsing that family
of XML is already the icd10cm repo's job, if this is ever revisited.

COUNTER-EXAMPLE WORTH KEEPING: DRG condenses beautifully — 775 bytes for all 871 codes, 22% of
raw — and it is the one vocabulary where condensing is worthless. Only 3 of its 871 codes are
unique across all 131 vocabularies (807 are also ICD9CM, 772 CIEL, 663 Multum, 580 HemOnc). The
vocabularies that condense well are the ones that do not need it, because a dense small numeric
code space is exactly what everyone else also occupies.

WHAT SUPERSEDES IT: exact membership matching in the consumer. Screen with the permissive regex,
then intersect against the real code list for each vocabulary; that yields 1x precision for free
and returns a CANDIDATE SET of vocabularies, resolved by context via vocabulary_labels.tsv. Under
that design stage-1 permissiveness is CORRECT rather than a defect — the regex's only job is to
be a cheap prefilter that misses no real code. The condensed grammar is the answer only for a
consumer that CANNOT reach a vocabulary. Handed to litmine 2026-08-17 as an architecture question
for that repo to answer; it is not a formats change.

Related: \[[vfm-k2n]\] (default = claims-observable), and the global ambiguity ceiling — 93.4% of
distinct OHDSI code strings are claimed by exactly one vocabulary, so membership is drastically
more discriminating than shape, which is what makes stage 2 worth building at all.

Evidence: claude_stuff/grammar-condensation-20260817-152741.log
claude_stuff/code-collision-20260817-151740.log
