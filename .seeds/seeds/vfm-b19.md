---
id: vfm-b19
title: "DEFERRED: what does a bare 'Read' label mean — Read V2 vs CTV3 adoption is unknown, so it gets no registry row until Read work starts"
status: deferred
type: question
created_at: 2026-09-30T18:13:48.710036+00:00
updated_at: 2026-09-30T18:13:49.299278+00:00
tags:
  - read
  - ctv3
  - registry
  - needs_context
  - deferred
  - ryan
  - 2026-09-30
---

RULED (Ryan, 2026-09-30), while settling vocabulary_formats-7j0: "this needs to be deferred until we start working with Read codes as I have no idea the adoption of v2 vs v3 and what's out in the wild and what's said in publications".

## The question

code_collector's AMBIGUOUS dict carries bare "read" -> "Read V2 vs Read V3/CTV3 — only Read (V2) is in the release". Moving that dict into vocabulary_labels.tsv (7j0) forced a status for it. None of them fits cleanly yet:

- needs_context needs at least two candidates (lint, ruled on yq4). The substrate has ONLY `Read` (NHS Read Codes Version 2, 108,946 concepts, vocabulation build 2026-09-17). There is no CTV3 vocabulary_id.
- mapped -> Read was proposed on the "best-effort map, the concept DB is the backstop" stance (vfm-31w). It was not taken, because nobody knows how often "Read" in the wild means V2 vs CTV3.

## What happens meanwhile

Bare "Read" gets NO row. Under the registry contract (vocabulary_formats-wyf) a missing row means UNADJUDICATED: surfaced and counted, never silently dropped. That is the honest state for a question nobody has looked into. Explicit "Read v2" spellings are unambiguous and do get a mapped row -> Read.

## Reopen when

Read-coded code sets are being produced. First measure: how often papers print bare "Read" vs "Read v2"/"CTV3"/"Read v3", which the unseen-label counts from code_collector will show; and whether CTV3 has entered the release (CTV3 was folded into SNOMED CT UK in 2020, so it may never arrive as its own vocabulary).
