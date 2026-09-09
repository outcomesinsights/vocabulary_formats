---
id: vfm-8l5
title: 'NDC: the committed regex rejected 338,328 real codes (26% of the vocabulary); default becomes 11-digit (claims), NDC.COMPLETE carries 9+11'
status: captured
type: decision
created_at: 2026-07-27T18:46:14.967279+00:00
updated_at: 2026-07-27T18:46:14.967295+00:00
tags:
  - ndc
  - false-negative
  - claims
  - billable
  - complete-variant
  - alphanum
  - odie
  - ryan
  - 2026-07-27
converted_at: 2026-09-02T14:41:48.760748+00:00
---

DISCOVERED by Odie 2026-07-27 while extending the regexes, verified independently the same day.

## The bug

```
NDC  ^\d{11}$  vs 1,302,950 real concept_codes  ->  **338,328 false negatives (26%)**
```

Of those, 337,085 are 9-digit NDCs and 1,218 are 9-digit Devices. This is the largest false-negative
count in the repo by a wide margin — 170x the ICD10CM regression fixed earlier the same day (1,953).
It had been shipping since the repo's first commit.

## WHY it happened — and this is the useful part

The 9-digit form is not an error or a legacy artifact. OHDSI classes them explicitly:

```
    len=11  class '11-digit NDC'   953,259    <- labeler-product-PACKAGE: the billing form
    len= 9  class '9-digit NDC'    337,085    <- FDA labeler+product, no package segment
    len=11  class 'Device'          11,388
    len= 9  class 'Device'           1,218
```

So the regex was correct for CLAIMS and wrong for the VOCABULARY, and nobody had written down which
of those the row was for. The bug is a symptom of the missing purpose statement — see the
two-consumer principle seed.

## DECIDED (Ryan, 2026-07-27)

```
NDC           ^\d{11}$              <- claims default (the billing form)
NDC.COMPLETE  ^(\d{9}|\d{11})$      <- the full vocabulary
```

Ryan: 'perhaps we should also have ndc.complete as 9 and 11 and default ndc to 11 only — my primary
goal for vocabulary_formats is to find codes we'd expect to see in claims data.'
This supersedes Odie's fix, which widened the DEFAULT to `^(\d{9}|\d{11})$`. His widening was right
about the facts and wrong about which row should carry them: it made the default mean 'everything in
the vocabulary', which is the drift the principle seed forbids.

## LETTERS IN NDC — asked and answered (Ryan)

'Is a letter ever a valid part of an NDC code?' **Yes, but barely: 39 of 1,302,950 (0.003%).**

```
    len=11  '11-digit NDC'  valid      24
    len= 9  '9-digit NDC'   valid      14
    len=11  '11-digit NDC'  invalid=D   1
```

38 are VALID concepts and OHDSI classes them as ordinary 9-/11-digit NDCs despite the letter. They are
radiopharmaceutical kits ('KIT FOR THE PREPARATION OF TECHNETIUM TC 99M...'), and they do NOT share a
single labeler prefix. So NDC.ALPHANUM earns its keep as a genuine long tail — but 39 codes is not a
reason to loosen any default.

## METHODOLOGY TRAP worth recording

A first pass answering the letters question used DuckDB's `~` operator and reported ZERO. **DuckDB's
`~` is NOT a regex-match operator** — `SELECT '000199092B0' ~ '[A-Za-z]'` returns FALSE while
`regexp_matches('000199092B0','[A-Za-z]')` returns TRUE. Any validation in this repo must use
regexp_matches or scan in Python; `~` will silently report false negatives as clean.
