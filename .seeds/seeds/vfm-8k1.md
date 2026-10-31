---
id: vfm-8k1
title: 'Declare case-insensitivity explicitly: patterns are case-exact unless a row says otherwise ("i16.5" should not pass ICD10CM)'
status: captured
type: decision
created_at: 2026-10-31T13:42:05.631880+00:00
updated_at: 2026-10-31T13:42:05.631880+00:00
tags:
  - case
  - case-sensitivity
  - ruling
  - validator
  - detector
  - conceptql-handoff
  - ryan
  - 2026-10-31
---

## The ruling (Ryan, 2026-10-31)

Ryan, verbatim, in a conceptql session: "if a code should be case insensitive, the
vocabulary_format regexp should explicitly list case insensitivity. call me a stickler, but I think
ICD-10-CM code i16.5 just doesn't look right and shouldn't be repected".

He then ruled for conceptql (seed `conceptql-oji` in the conceptql repo): codes match case-exactly
by default. A vocabulary is case-insensitive only when its vocabulary_formats row declares it.
conceptql honors that declaration in its format check and in its concept lookup.

The consequence for this repo: a regexp in `vocabulary_formats.tsv` is case-exact unless the row
declares case-insensitivity explicitly. A row that admits lower case only through `[A-Za-z]`,
`[a-z]` or `\w` is an implicit declaration, and the ruling says that is not enough.

## The current table (checked against `vocabulary_formats.tsv` at e1889b4)

No row uses an inline `(?i)` flag. The table has no case column.

These rows admit lower case without saying so:

- `ICD10CM` `(?:QA[0-9]|[A-Za-z][0-9][0-9ABab])(\.[0-9A-Za-z]{1,4})?` and `ICD10CM.DOTLESS`.
  The ruling's example `i16.5` passes `ICD10CM` today.
- `ICD10` and `ICD10.DOTLESS` (letter positions and the `\w` tail). Their Roman-numeral chapter
  branch is upper case only.
- `ICD10PCS` `[0-9A-HJ-NP-Za-hj-np-z]{1,7}`.
- `HCPCS` `[A-Za-z]\d{4}` and `HCPCS.WITHMODIFIERS`.
- `CPT4` `\w\d{3}\w` and `CPT4.WITHMODIFIERS` (`\w` admits lower case).
- `CPT4_HCPCS`, `CPT4_HCPCS.WITHMODIFIERS`, `CPT4_HCPCS.CODEONLY`.
- The modifier rows `HCPCS_MODIFIER`, `CPT4_MODIFIER`, `CPT4_HCPCS_MODIFIER` (`\w{2}`).
- `ATC` (both letter classes), `NDC.ALPHANUM` (`\w`), `EDI` (`\w`).
- `ICDO3`, `ICDO3.CODEONLY`, `ICD03_Topography`, `ICD03_Topography.DOTLESS` (`[A-Za-z]`).
- `SNOMED.WITHRETIRED` admits both cases of hex in its UUID branch.

These rows are already upper case only: `ICD9CM` and `ICD9CM.DOTLESS` (`V`, `E`),
`ICD10PCS.BILLABLE` `[0-9BCDFGHX][0-9A-HJ-NP-Z]{6}`, and `RxNorm Extension` (`OMOP`). So the table
is already inconsistent: `ICD10PCS` accepts `0dtj0zz` while its own `.BILLABLE` variant does not.

## An earlier decision that this ruling reverses

The `ICD10PCS` row's notes say: "Case stays permissive on purpose - every published code is
uppercase and [0-9A-HJ-NP-Z]{1,7} would cut the tabular figure to 1,695, but a caller that
lowercases before validating would then get a silent 100% false-negative rate." Seed vfm-yop
repeated it ("Case stays permissive"). The ruling moves that concern to the caller. A caller that
changes the case of a code before it validates must also say so, or use a row that declares
case-insensitivity. The note must change when the row changes.

## Facts about the codes

- The OHDSI vocabulary stores the codes of these vocabularies in upper case.
- In conceptql's synpuf test vocabulary, the lower-case `concept_code` values in the claims
  vocabularies are: NDC 3 (for example `1549912340a`), ICD9CM 1 defect row (`sd`), and LOINC 2
  survey codes. ICD10CM, ICD10PCS, HCPCS, CPT4 and DRG have none. (Measured by the conceptql
  session on its test fixture, not on a full Athena release. `just test` must confirm it on Athena
  for each row that is narrowed.)

## Consumers that already handle case themselves

- codesistant `shapes.py` compiles every row as `(?:row)` with `re.IGNORECASE`. It makes every row
  case-insensitive, whatever the row says. If rows begin to declare case, codesistant must stop
  adding the flag, or the declaration has no effect there.
- codesistant `canonicalize.py` and `explode.py` upper-case codes before they use them.
- conceptql wraps each regexp as `\A(?:row)\z` in Ruby. It consumes a pinned copy
  (`config/vocabulary_formats.tsv` and `.sha`) and refreshes it with `just vocabulary-formats <ref>`.
  conceptql waits for the decision here before it builds its side.

## Open questions (not ruled)

1. How does a row declare case-insensitivity? Two candidates:
   - An inline flag in the regexp. A global `(?i)` is safe only at the very start of a pattern:
     Python 3.11 and later raise an error for a global flag that is not at the start, and every
     consumer wraps the row in `(?:...)` or `\A(?:...)\z`, which puts it inside. The scoped form
     `(?i:...)` works in Python, Ruby, PCRE and RE2 (DuckDB). `just lint`'s anchor and
     top-level-alternation scanner must accept it. Not tested yet in each consumer.
   - A new column (for example `case_insensitive`). Every consumer must read it, or it has no
     effect. A consumer that ignores the column silently gets case-exact matching.
2. Which rows become upper case only, and which rows (if any) declare case-insensitivity? The
   ruling makes case-exact the default, so the likely answer is "most rows become upper case only".
   Each narrowed row needs `just test` (no new false negatives) and a `CHANGELOG.md` entry.
3. What happens to detectors? Rows with `use` containing `detector` find codes in prose, where
   lower case can be common. This table also serves code_collector and codesistant. A detector may
   need different behavior from a validator (see vfm-6x1, "A validator and a detector want opposite
   things"). One option: the detector caller declares case-insensitivity itself, as codesistant
   does today. Another option: a separate variant row for detection.
