---
id: vfm-9ug
title: 'conceptql will validate codes with vocabulary_formats: rows needed for LOINC and Gemscript'
status: captured
type: question
created_at: 2026-10-30T12:34:38.848517+00:00
updated_at: 2026-10-30T12:34:38.848517+00:00
tags:
  - conceptql
  - cross-repo
  - handoff
  - loinc
  - gemscript
  - consumer-contract
  - claims-observable
  - 2026-10-30
---

## Handoff from conceptql (facts verified 2026-10-30 in conceptql, not in this repo)

conceptql is the ConceptQL query-language gem. It translates clinical algorithm statements into SQL.
These facts were measured in conceptql. This seed hands them over. It does not rule on anything here.

### The decision in conceptql

- Ryan ruled in conceptql on 2026-10-30 that conceptql must stop maintaining its own code-format
  regexps and must use vocabulary_formats instead.
- conceptql's current patterns live in its `config/vocabularies.csv`, column `format_regexp`. They
  are anchored `^...$`.
- Since a recent unreleased change in conceptql, a code that fails the format is a validation
  ERROR. The statement is invalid and cannot run. So a pattern that rejects a real code blocks an
  algorithm. That is the same false-negative contract this repo already holds itself to.

### conceptql vocabularies that have a format today

ATC, CPT4, CPT4_HCPCS, DRG, Gemscript, HCPCS, ICD03_Morphology, ICD03_Topography, ICD10, ICD10PCS,
ICD10CM, ICD9CM, ICD9Proc, LOINC, NDC, RxNorm, SNOMED.

Two of these have no row in `vocabulary_formats.tsv` today: LOINC and Gemscript. (`vocabulary_labels.tsv`
already has a `LOINC` label row, status `mapped`.)

### LOINC

- An adversarial review in conceptql found that conceptql's own LOINC pattern rejects 99 standard,
  valid LOINC Lab Test codes. The pattern is:

  ```
  ^\w{3,7}-\w$
  ```

- The rejected codes have 1 or 2 digits before the dash. Examples: `1-8` (Acyclovir susceptibility)
  and `20-8` (Amoxicillin+Clavulanate MIC). `20-8` is concept_id 3023414.

- vocabulary_formats has no LOINC row today.

### Gemscript

- conceptql's pattern is:

  ```
  ^\d{8}$
  ```

- Measured in the OHDSI vocabulary of conceptql's DuckDB test fixture (`ohdsi_vocabs.concept`):

  - Gemscript has 260,691 codes. 246,376 of them are 8 digits.
  - 1,631 codes start with `!`. Of those, 306 have no `invalid_reason`, 171 have
    `valid_end_date >= 2026-01-01`, and 135 are standard.
  - Samples such as `!5019103` (NYSTAFORM-HC) and `!8504035` (BECLOMIST AQUEOUS NASAL SPRAY) are
    mostly `invalid_reason` D, valid 2018-07-01 to 2020-07-31.
  - One is `!2621701`, named "(name unavailable)", class Clinical Finding.

- The counts above do not add up to 260,691. The rest of the shapes were not broken down in
  conceptql.

- vocabulary_formats has no Gemscript row today.

### CPT4 and HCPCS modifiers

- Modifiers such as `25` and `A1` fail conceptql's patterns. vocabulary_formats already has
  `CPT4.WITHMODIFIERS`, `HCPCS.WITHMODIFIERS` and the `*_MODIFIER` rows.
- Ryan's position: conceptql does not support CPT4 class codes (for example the 7-digit `1028555`,
  Global period). So it is fine that conceptql rejects those.
- Whether modifiers belong in conceptql's accepted set is open on the conceptql side. It is not a
  question for this repo.

## Questions for vocabulary_formats (not ruled)

1. Should this repo add a LOINC row? If yes, which variants: only the `NNNNN-N` test codes in the
   default row, or also the LP (part), LA (answer) and LG (group) codes in named variants?
2. Should this repo add a Gemscript row (8 digits)? Are the `!` codes in scope for the default row
   under the claims-observable policy (vfm-k2n), or do they belong in a named variant such as
   `.WITHRETIRED`? Note that some `!` codes are still valid and standard in the fixture.
3. Is there anything conceptql should know about consuming the default rows? The current
   understanding in conceptql: the published patterns are bare, so conceptql must bind them as
   `\A(?:...)\z` in Ruby, never `^...$`. conceptql would also need to pick, per vocabulary, which
   row (default or a variant) it binds to.
