---
id: vfm-8k1
title: 'Declare case-insensitivity explicitly: patterns are case-exact unless a row says otherwise ("i16.5" should not pass ICD10CM)'
status: captured
type: decision
created_at: 2026-10-31T13:42:05.631880+00:00
updated_at: 2026-10-31T14:17:25.991281+00:00
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

## Census of lower case in Athena (2026-10-31)

Measured on the full Athena `CONCEPT.csv` (100,035 ICD10CM codes). Log:
`claude_stuff/lowercase-census-20261031-064947.log` (not committed).

```
vocabulary_id     total      lower  lower_and_valid
ATC                 7,327        0      0
CPT4               18,068        0      0
DRG                 1,362        0      0
EDI               442,551        0      0
Gemscript         260,517      179      0   (manufacturer names: 'Abbott', 'Actavis')
HCPCS              12,670        0      0
ICD10              16,638        0      0
ICD10CM           100,035        0      0
ICD10PCS          197,098        0      0
ICD9CM             17,564        1      0   ('sd')
ICDO3              64,471        0      0
LOINC             277,764        2      2   ('SURVEY.howRU', 'PANEL.SURVEY.howRU')
NDC             1,302,950        3      3   ('1549912340a', '1549912340b', '5812800010a')
RxNorm            315,157        0      0
RxNorm Extension 2,171,452       0      0
SNOMED          1,093,147  464,018      0   (every UUID-shaped code; all lower-case hex)
```

So every vocabulary that has a row today is upper case, with two exceptions. The SNOMED UUIDs
(only `SNOMED.WITHRETIRED` covers them) are all lower case. Three valid NDC codes contain a
lower-case letter, and today they pass `NDC.ALPHANUM` only because `\w` admits lower case.

Case-exact does not mean upper case. `SNOMED.WITHRETIRED` can narrow its hex to `[0-9a-f]`.

## RULED 2026-10-31 (Ryan): the three open questions

Ryan, verbatim: "I agree with the reccomendations."

1. **Mechanism:** a row declares case-insensitivity with the scoped inline flag `(?i:...)`. There
   is no new column. Reason: a consumer that cannot parse the flag fails loudly, but a consumer
   that ignores a column matches the wrong way with no error. `just lint` accepts `(?i:...)` and
   rejects a global `(?i)`.
2. **Rows:** no row needs the flag today. Every row becomes case-exact. Each `\w` and each
   lower-case range is replaced by an explicit class. `SNOMED.WITHRETIRED` narrows to lower-case
   hex. The `ICD10PCS` note "Case stays permissive on purpose" is rewritten. Each narrowed row
   needs `just test` and a `CHANGELOG.md` entry.
3. **Detectors:** the caller adds case-insensitivity, as codesistant does today. No separate
   detector rows. This matches the repo rule that usage-specific behavior belongs in the caller.

Dependency outside this repo: codesistant `shapes.py` adds `re.IGNORECASE` to every row. A row
that declares nothing is still case-insensitive there. That is correct for codesistant's detector
use. For its validator use, codesistant must stop adding the flag, or the ruling has no effect
there. conceptql waits for this decision before it builds its side.

## The three lower-case NDC codes are defects (verified 2026-10-31)

Ryan asked to verify that the three codes are bad before they are excluded. They are bad.

- **Athena:** all three are "OXYGEN - oxygen gas", class "11-digit NDC", valid, with no
  relationships and no synonyms. Each sits beside numeric siblings of the same product:
  `15499123401`..`15499123409` and `58128000100`..`58128000109`.
- **The source label:** DailyMed SPL setid `1df5a2d7-fb0f-49b1-981b-d019f436750c`
  ("OXYGEN (OXYGEN ) GAS [FIRST CHOICE MEDICAL EQUIPMENT INC.]", version 1, published
  2010-07-19, never revised) lists packages `15499-1234-1` to `15499-1234-9`, then
  `15499-1234-a` and `15499-1234-b`. The labeler used a 5-4-1 layout, ran out of digits in the
  one-digit package field, and continued with letters. OHDSI padded them to 11 characters.
  `5812800010a` follows the same pattern (packages `-00` to `-09`, then `0a`). No SPL for
  `58128-0001` is on DailyMed today, so that one is inferred from the pattern.
- **The regulation:** 21 CFR 207.33(a): "The NDC for a drug is a numeric code." Each segment
  "consists of" digits.
- **NLM RxNav `ndcstatus`:** all three return `UNKNOWN` with no source and no history. The
  numeric siblings return `ACTIVE` (`15499123401`, MTHSPL and RXNORM) or `OBSOLETE`
  (`58128000101`).
- **The current FDA NDC directory** (openFDA) has neither product.

Logs (not committed): `claude_stuff/ndc-lowercase-20261031-065224.log`,
`ndc-lowercase-rel-20261031-065322.log`, `ndc-spl-20261031-065351.log`,
`cfr-207-33-20261031-065424.log`, `ndc-rxnav-20261031-065439.log`.

Consequence: exclude the three codes from `NDC.ALPHANUM`'s target in
`checks/validation_targets.json`, with this evidence. Do not declare the row case-insensitive for
them. The 38 upper-case alphanumeric NDC codes (vfm-cd0) are also non-numeric under 207.33, but
they are upper case and outside this ruling.

Hazard for the test: `1549912340a` is 11 characters. If `NDC.ALPHANUM` narrows to upper case,
`just test` reports these three as false negatives until the exclusion lands in the same change.

## UPDATE 2026-10-31: the three oxygen codes are excluded for case only

Ryan later ruled (seed vfm-5g7) that letters in NDC segments are respected, because legacy NDCs
allowed them and no evidence shows these codes did not exist. So the section above that calls the
three lower-case codes "bad" holds only for their lower-case spelling. An upper-case spelling such
as `1549912340A` belongs in `NDC.ALPHANUM`'s target and must pass the row after it becomes
case-exact.
