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

## The patterns carry NO anchors — the caller supplies the boundary

**Every `regexp` value matches a complete code and nothing more, but it is stored without `^`, `$`, `\A`, `\z` or `\b`.  Binding it to a boundary is the caller's job, and the caller must do it.**

Do not treat this as a small ergonomic detail.  Used bare, a pattern matches a code *inside* a longer string, so `I10 and some trailing prose` passes the `ICD10CM` row.  And for the short rows it is far worse than that: `HCPCS_MODIFIER`, `CPT4_MODIFIER` and `CPT4_HCPCS_MODIFIER` are all `\w{2}`, and `DRG` is `\d{3}`.  Unanchored, `\w{2}` is true for **any** value containing two consecutive word characters — the check does not weaken, it stops existing.

This is deliberate, because the correct anchor differs by language and by job:

| Language | Whole-string validation |
| --- | --- |
| Ruby | `/\A(?:#{pattern})\z/` — **not** `^…$`, which are LINE anchors in Ruby, so `"A00\nDROP TABLE codes"` would pass |
| Python | `re.fullmatch(pattern, s)`, or `re.compile(rf"\A(?:{pattern})\Z")` |
| R, base | `grepl(paste0("^(", pattern, ")$"), x, perl = TRUE)` |
| R, stringr | `str_detect(x, paste0("^(", pattern, ")$"))` — `str_detect` alone is an unanchored search.  stringr is ICU, not PCRE, and takes no `perl =` argument |
| SQL / DuckDB | `regexp_full_match(code, pattern)` |

To *find* codes inside free text rather than validate a known string, anchor on code boundaries instead of string ends — `(?<![0-9A-Za-z])(?:PATTERN)(?![0-9A-Za-z])`.  Shape alone is rarely enough for prose: a scanner usually also needs context (a parenthetical, or a lead-in such as "codes" or "classifiable to").  See the Principles in `CLAUDE.md`.

**Wrap the pattern in a non-capturing group when you anchor it.**  Several rows are alternations, and `\A` + `a|b` + `\z` binds the anchors to the first branch only.  Every row is a single self-contained expression so that `(?:…)` always works — keep it that way when adding rows.

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
Those are deliberately **not** matched — an exclusion is always a documented decision, never a silent
miss.

Classification tiers are excluded the same way and for the same reason: `CPT4 Hierarchy` groupers and
`HCPCS Class` (BETOS) categories are not billable codes.

**That validation re-runs — it is not a claim in the `notes` column.**  `checks/validation_targets.json`
declares as data what each row is held to: which `vocabulary_id`s and `concept_class_id`s make up its
target, whether retired concepts count, any code transform (`.DOTLESS`, `.UNPADDED`, `.NOBEHAVIOR`),
and every deliberate exclusion **with the evidence** — `concept_id`, `invalid_reason`,
`concept_class_id` — that makes it not-a-code.  `just test` pulls each target out of the concept
table and requires every code in it to match that row's regexp, bound the way a caller binds it.  As
of 2026-08-13 all 34 rows score **0 false negatives over 8,662,422 codes**.

A row's target is its *own*, never the whole vocabulary: the 9-digit NDCs the claims-default `NDC`
row rejects are out of target and correct, while the same codes failing `NDC.COMPLETE` would be a
bug.  Changing what a row is held to means editing that declaration, in the open, next to the reason.

## Commands

```bash
just lint    # THE GATE. Structural: regexps compile, no anchors, no top-level alternation,
             # unique keys, parquet in sync with the TSV, every row's target declared.
             # No database, no network, seconds — run it before every commit.
just test    # The false-negative harness above. Needs an OHDSI concept table and skips
             # cleanly, with a message, when there is not one on the machine.
make all     # Regenerate both parquets after editing a TSV (`just parquet` calls this).
```

Both commands tee a timestamped log into `claude_stuff/` and print its path.  `just test` reads its
substrate from `VOCABULARY_FORMATS_ATHENA_CSV` (a stock Athena `CONCEPT.csv`) and
`VOCABULARY_FORMATS_OI_DUCKDB` (a `vocabulation` build, the only place the OI-minted vocabularies
`CPT4_HCPCS` and `ICD03_*` exist); defaults for both are in the declaration file.

## Contributing

Contributions are welcome!
