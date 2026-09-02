---
id: vfm-bmg
title: multi_vocabulary rows leave the producer re-parsing PROSE — should the registry carry component vocabulary_ids?
status: captured
type: question
created_at: 2026-08-04T15:13:40.787589+00:00
updated_at: 2026-08-04T15:13:40.787597+00:00
tags:
  - registry
  - multi-vocabulary
  - split
  - rule-4
  - litmine
  - producer
  - omission
  - 2026-08-04
converted_at: 2026-09-02T14:41:48.760748+00:00
---

A `multi_vocabulary` row records that a label names more than one vocabulary, leaves `vocabulary_id`
blank, and README says the remedy is "a producer-side split into per-vocabulary code sets, not a
single mapping." The POLICY is settled (habitat rule 4: one vocabulary per code set). The DATA to
execute it is not here.

## The problem, in one row

    label          mixed procedure codes (CPT, CPT Category III/PLA, HCPCS Level II, ICD-10-PCS);
                   labeled only "Procedures" by the authors
    vocabulary_id  (blank)
    status         multi_vocabulary
    notes          FLAGGED, do not map. CPT4_HCPCS would silently drop the ICD-10-PCS members.

Everything a producer needs to perform the split is present — and present only as PROSE, inside a
free-text label and a free-text note. To act on it, a producer must re-read English and infer
{CPT4_HCPCS, ICD10PCS}. That is a model decision standing in for a lookup, which is exactly what
Mark's invariant #4 ("routing decisions that can be computed are computed") says not to build, and
exactly the failure mode that motivated killing the extraction-time vocabulary enum (lit-et6.4): a
model re-deriving something a table could state.

The second such row makes it sharper, because its components are NOT recoverable from prose alone:

    ICD-9-CM / ICD-10-CM (mixed; printed as one unlabeled list)

Here the split is not even a partition by label — it needs per-CODE adjudication, since the paper
printed one undifferentiated list. Two multi_vocabulary rows, two different kinds of split.

## The question

Should a `multi_vocabulary` row carry its COMPONENT vocabulary_ids as data — a delimited list in a
new column, or the row expanded into several — so the producer's split is a lookup?

Points to weigh:

- **For:** it is the same argument that won lit-et6.4. Whoever adjudicated the row already knew the
  components; discarding that into prose forces every downstream consumer to re-derive it.
- **For:** it makes the split auditable. A component list can be checked; an inference cannot.
- **Against:** the two rows split by different MECHANISMS. Row 1 partitions by code format
  (a CPT code and an ICD-10-PCS code are distinguishable by shape, so the format regexps can route
  them). Row 2 needs code-by-code adjudication against the concept table, because ICD-9-CM and
  ICD-10-CM overlap in shape. A single "components" column would imply these are the same operation
  when they are not — and might invite a producer to attempt row 2 mechanically and get it wrong.
- **Against (scope):** this repo is data-only and deliberately dumb. A components column edges toward
  encoding an algorithm in the table.
- **Middle option:** carry the components AND a `split_by` discriminator (`format` vs `lookup`), so
  the data says both what the parts are and whether they are mechanically separable.

## Why it matters more now than at the pilot

Two multi_vocabulary rows out of 22 came from 20 papers. Verbatim extraction across 11K+ papers
(Ryan, 2026-08-04) will produce these at volume, and every unresolved one is a real code set dropped
— the omission failure habitat rule 7 names. At two rows a human can read the prose. At two hundred
they cannot.

## Not to be resolved here alone

The consuming side is the producer's renderer (code_collector after the litmine merge). Whatever this
seed concludes, the split itself is filed there, and habitat routing says new mappings go to a domain
agent (Odie or Vincent) to author and validate rather than being guessed producer-side.

Related: vfm-31w (the registry's design), and beads vocabulary_formats-wyf / -7dl (the two contract
items filed 2026-08-04).
