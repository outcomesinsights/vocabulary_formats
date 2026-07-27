# vocabulary_formats

PCRE that verify the correctness of codes used in various medical terminologies

## Why?

In dealing with various medical terminologies, there are occasions when we need to ensure we are using valid codes from sources such as claims data, vocabulary files, or user-entered data.  It is not always feasible to compare these codes to a database of known valid codes.  The database may not be up-to-date.  There might be codes that are unknown to the database.  Access to the database might be difficult to set up.

Sometimes it's easier to see if a code "looks" like a valid code, hence these regexps.  The goal is to provide a set of regexps that verify if a code from a given terminology "looks" like the kind of code we expect.

## What the Default Row Targets: Claims-Observable Codes

**The primary goal is to recognise codes we would expect to see in claims data — mostly billable.**  For each vocabulary, the DEFAULT row targets that.  Anything broader — the full vocabulary, retired concepts, alternate encodings — belongs in a **named variant**, never in the default.

This has always been the intent; it simply was not written down.  The `.DOTLESS` variants exist because Medicare claims data often reports those codes without the dot, which is a claims-shaped concern from the repo's first commit.

Two consumers pull in opposite directions here, which is why the split matters:

1. **Claims canonicalization** — billable, claims-observable codes, canonicalized before an exact join against a concept table.
2. **Literature validation** — any real code a paper printed, including vocabularies that never appear on a US claim.  SNOMED is in this repo for this reason, not because it shows up in claims.

Variants serve both without either winning.  The failure mode to guard against is the **default quietly widening to mean "everything real"**: that is how the `NDC` row came to reject 26% of its own vocabulary while nobody noticed the purpose had blurred.

Corollary for the two tables: `vocabulary_formats.tsv` answers *"does this look like a code of vocabulary X?"*, and `vocabulary_labels.tsv` answers *"what vocabulary is this label naming?"*.  Neither answers *"is this a real code?"* — that is a lookup against the concept table, and it belongs to the caller.

## Skewed Towards Valid

If a choice has to be made between a more restrictive or a more permissive regexp, we'll favor the more permissive.  The point of these regexps is to see if a code _could_ be possibly valid.  If the goal is to ensure that only known, valid codes are permitted, these are not the regular expressions to use.

**False negatives are judged against the row's declared target, not against the whole vocabulary.**  A 9-digit NDC failing the claims-default `NDC` row is correct; the same code failing `NDC.COMPLETE` is a bug.  Within a row's stated target, a false negative is never acceptable.

If the regexps are too restrictive, they might disqualify future valid codes.  For example, ICD10CM recently introduced codes that start with U, particularly for the diagnosis of COVID-related symptoms.  There are regexps in the wild that would mark these new codes as invalid.  That kind of regexp is overly restrictive for our purposes.

Basically, if the regexp yields a false negative, it's not an acceptable regexp.  If it yields a small number of false positives, we'll allow it.

## Tab Seperated Values (TSV) Format

This repository contains a TSV file of regexps that have been gathered from various sources.  Tabs were chosen over commas to avoid needing to quote regexps that contain commas.  This file is intended to be modified.

### Parquet Format

We needed a Parquet file for one of our projects, so we created it and decided to share it.

Run `make all` to generate the Parquet file.

Here are the columns:

- vocabulary_id
  - Preferably the OMOP-related vocabulary_id associated with the terminology
  - e.g. ICD9CM, NDC, CPT4
  - variants
    - If the regexp is meant to apply to a specific variation of the expected code format, add a suffix to the vocabulary_id
    - e.g. ICD9CM and ICD10CM codes are often reported in Medicare claims data without the "." (dot) in the code so we'd name them ICD9CM.DOTLESS and ICD10CM.DOTLESS
- regexp
  - The PCRE that matches the codes in the terminologies.  
- source
  - URL to where regexp was found, if applicable
- notes
  - Information relevant to the regexp, such as limitations, reason for the variant, etc

## `vocabulary_labels.tsv` — the id-normalization registry

A second table, in the same TSV + Parquet shape, answering a different question: **"a document called
its vocabulary _X_ — which `vocabulary_id` is that?"**  The format regexps say what a code should look
like; this says which vocabulary a label refers to.  The two join on `vocabulary_id`.

It is a **registry, not just a mapping**.  Every label encountered in the wild is recorded *verbatim* —
the verbatim string is the row key, so provenance is never lost — and each row resolves to either a
`vocabulary_id` in our substrate or a **blank**.  A blank is load-bearing: it makes an unsupported
vocabulary *visible* instead of letting a code set silently vanish.  Consumers use the blanks as an
extract-but-don't-produce gate.

Columns:

- `label` — the vocabulary name exactly as it appeared in the source.  Never normalized; lookups
  should normalize case/whitespace on the consumer side.
- `vocabulary_id` — the target in our substrate, which **includes OI supplemental vocabularies**
  (e.g. `CPT4_HCPCS`), not just stock OHDSI ids.  Blank when unresolved.  Blank in the TSV reads back
  as NULL from the Parquet; both mean the same thing.
- `status` — why the row is where it is.  Three values, and the distinction matters because two of
  them share a blank `vocabulary_id` for entirely different reasons:
  - `mapped` — resolves to a `vocabulary_id`.
  - `unsupported` — not in OHDSI or our supplementals *as of now*.  Revisit when a release adds it.
  - `multi_vocabulary` — the label names more than one vocabulary.  The remedy is a producer-side
    **split** into per-vocabulary code sets, not a single mapping and not waiting on OHDSI.
- `source` — where the label was observed, with counts.
- `notes` — anything a future reader needs so they don't "fix" a deliberate decision.

Note that a mapping may deliberately **widen**: `CPT` maps to `CPT4_HCPCS`, which covers CPT *and*
HCPCS.  That is correct for binding — a CPT code resolves in the hybrid — and costs nothing, because
the verbatim label stays the row key.

## What "never reject a real code" is measured against

Every regexp here is validated against the real `concept_code` values in an OHDSI build before it
ships.  A handful of vocabularies also contain rows that are *not codes*: UMLS source markers
(`V-CPT`, `V-SRC`), OMOP metadata (`Global period 90 days`), placeholder rows whose `concept_code` is
just the `concept_id` (`45532996`, named "Invalid ICD10 Concept, do not use"), and upstream defects.
Those are deliberately **not** matched, and each row's `notes` enumerates exactly what it excludes and
why — so an exclusion is always a documented decision, never a silent miss.

Classification tiers are excluded the same way and for the same reason: `CPT4 Hierarchy` groupers and
`HCPCS Class` (BETOS) categories are not billable codes.

## Contributing

Contributions are welcome!
