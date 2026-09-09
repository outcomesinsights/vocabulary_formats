---
id: vfm-31w
title: 'Add a SECOND table: the vocab-label id-normalization REGISTRY (verbatim label seen in the wild -> OHDSI vocabulary_id, or BLANK = not supported in OHDSI)'
status: captured
type: decision
created_at: 2026-07-25T17:46:20.650965+00:00
updated_at: 2026-08-04T15:02:46.718775+00:00
tags:
  - id-normalization
  - registry
  - vocabulary-id
  - ohdsi
  - data
  - litmine
  - codesistant
  - cross-repo
  - 2026-07-25
converted_at: 2026-09-02T14:41:48.760748+00:00
---

Decided by Ryan across litmine's lit-et6.1 (2026-07-23 refinement) and refined 2026-07-24. Filed HERE
2026-07-25 during the codesets seed-reconciliation pass — the decision was fully specified but lived
only in litmine's seed tree, and this repo had no seeds at all.

## The decision

vocabulary_formats gains a SECOND table alongside the format regexes: an **ID-normalization map**
from a vocabulary label 'hit in the wild' -> a known-good OHDSI `vocabulary_id`.
Examples: 'ICD-10-CM' -> ICD10CM; WHO 'ICD-10' -> ICD10; 'CPT' / 'CPT-4' -> CPT4.

## It is a REGISTRY, not just a mapping (Ryan, 2026-07-24)

Every vocabulary label encountered in the literature is recorded **verbatim**, and each row resolves
to EITHER a known-good OHDSI vocabulary_id OR a **BLANK** id meaning 'this vocabulary is not
supported in OHDSI (as of now)'. Ryan's words: 'if the vocab doesn't exist, we record it as it
appears in the literature into that mapping file and either derive a mapping or leave the mapping
with no OHDSI ID to indicate that the vocab isn't supported in OHDSI.'

Consequences:

- The table is the COMPLETE registry of labels seen + their OHDSI status — one source of truth.
  A new unseen label is appended verbatim, then mapped or left blank.
- **A blank id IS the non-OMOP gate.** litmine's 'extract but don't produce' set (lit-et6.3) is
  exactly the blank rows; no separate list is needed.
- Provenance preserved (verbatim label is the key) and omission is VISIBLE — a blank loudly marks
  'not in OHDSI' rather than a code set silently vanishing.
- Blank means 'unsupported AS OF NOW' — revisitable when OHDSI or an OI supplemental vocab adds it.
- A genuinely MISLABELED code (a paper calls ICD10CM 'ICD-10') is caught downstream by the
  format/existence check. The map is best-effort; the concept DB is the backstop.

## Why it belongs here and not in code

Separation of concerns, decided with Ryan: **vocabulary_formats stays DATA-ONLY and polyglot** — the
Ruby catalog and both Python producers read the same files. Adding Python would break its
language-neutral value. The CODE that consumes it lives in **codesistant** (repo created 2026-07-23,
beads cst-\*), which reads BOTH tables (format regexes + id-normalization).

## Downstream consumers

- codesistant reads it for producer-side vocab-name alignment.
- code_collector's `vocab_mappings.csv` (21 rows, name -> OHDSI id) eventually MIGRATES here.
- Its non-blank ids feed the extraction-time enum litmine is considering (lit-et6.4) — deriving the
  enum from this column keeps the enum and the format regexes from drifting apart.

## Authoring

Hand the entries to a domain agent — Odie (OHDSI/OMOP) or Vincent (vocab) or the vocabulary habitat —
to author and validate, rather than guessing ids.

BEAD FILED 2026-07-25: **vocabulary_formats-e5s**.

## CPT4_HCPCS IS A FIRST-CLASS MAPPING TARGET (Ryan, 2026-07-25) — and the PREFERRED one for procedures

Ryan, raising this specifically: 'we'll especially need to do that with HCPCS/CPT as those are divided
in OHDSI and we unioned them.' The union exists and is verified in the substrate:

```
vocabulary_id **CPT4_HCPCS** — 30,357 concepts; CPT4 18,069 + HCPCS 12,822 = 30,891, 534 deduped.
vocabulary_version is NULL -> an OI SUPPLEMENTAL vocabulary, not stock Athena.
Decided in code_set_catalog csc-171 (2026-06-02); catalog-side wiring is bead csc-meqj.
```

### Why this changes the registry's spec as written above

This seed says each row maps to 'a known-good OHDSI vocabulary_id'. Taken literally that excludes
CPT4_HCPCS (it is an OI supplemental, not stock OHDSI) and pushes the naive mappings
'CPT' -> CPT4 and 'HCPCS' -> HCPCS — **which re-creates precisely the split csc-171 exists to heal.**

So: the target column is 'a vocabulary_id in OUR substrate', which INCLUDES OI supplementals.
CPT4_HCPCS is a legal, and for procedure labels the PREFERRED, target — matching csc-171's
'hybrid is the recommended default; originals stay selectable'.

### The concrete rows this affects (real labels from litmine's 20-paper pilot)

```
'CPT'          (23 code sets)  -> CPT4_HCPCS   (not CPT4)
'CPT-4'         (6)            -> CPT4_HCPCS
'HCPCS'         (4)            -> CPT4_HCPCS   (not HCPCS)
'CPT/HCPCS'     (1)            -> CPT4_HCPCS   <- has NO other home
'mixed procedure codes (CPT, CPT Category III/PLA, HCPCS Level II, ICD-10-PCS); labeled only
 "Procedures" by the authors' (1)            -> needs a call: CPT4_HCPCS loses the ICD-10-PCS
 part, so this may be a genuine multi-vocabulary set requiring a producer-side SPLIT (rule 4)
 rather than a single mapping. Flag rather than guess.
```

Without this, the last two map to BLANK and are silently dropped by lit-et6.3's
extract-but-don't-produce gate — a perfectly good procedure code set lost, which is exactly the
omission failure habitat rule 7 names as the primary risk.

### Note on 'preferred'

Mapping 'CPT' -> CPT4_HCPCS is a WIDENING: the label said CPT, the target covers CPT+HCPCS. That is
correct for BINDING (a CPT code resolves in the hybrid) but the verbatim label stays 'CPT', so no
provenance is lost. If a consumer ever needs the narrow reading, it has the verbatim key. Worth
stating explicitly in the table's notes column so a future reader does not 'fix' it back.

## THE REGISTRY IS NOW FED BY THE HARVEST (Ryan, 2026-08-04)

Ruling on the upstream-vs-downstream fork that this table was always the downstream half of:
**"extract vocabulary as it is written in the paper and we will use that information to form a
comprehensive mapping in vocabulary_formats."** Recorded in full on litmine's lit-et6.4.

**What it settles for this table.** There will be no closed vocabulary enum at extraction time. The
verbatim label is captured exactly as the paper spelled it, and THIS registry is the only place
normalization happens. That makes the table load-bearing rather than convenient: if a label has no
row, the code set it belongs to is dropped by the extract-but-don't-produce gate (lit-et6.3), so a
missing row is a silent data loss of exactly the kind habitat rule 7 names as the primary failure.

**What it changes about how the table GROWS.** The rows above came from a 20-paper pilot — 22
free-text labels for ~14 real vocabularies. The harvest is now planned against 11K+ papers
(code_collector clc-pdr, corrected 2026-08-04), so the observed-label set will be much larger and
will keep arriving. Two consequences:

1. **The registry is never complete before a harvest, and that is fine.** Design for continuous
   extension, not a one-time authoring pass. What is NOT fine is an unmapped label failing quietly —
   every miss must be surfaced and counted at render time so a human can decide whether it needs a
   row, a `multi_vocabulary` split, or a genuine `unsupported` blank.
2. **The harvest becomes this repo's best source of real-world labels.** Every way the literature
   actually spells a vocabulary, at volume. That is more comprehensive than anything authored from
   the OHDSI vocabulary list alone, and it serves every consumer of this table, not just the
   literature pipeline.

**Unchanged:** the target column is "a vocabulary_id in OUR substrate," including OI supplementals
(CPT4_HCPCS stays the preferred target for procedure labels, per csc-171), and mapping 'CPT' ->
CPT4_HCPCS remains a deliberate WIDENING that loses no provenance because the verbatim label is the
key. Authoring/validating new rows still goes to a domain agent (Odie or Vincent) rather than being
guessed by the producer.
